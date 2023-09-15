import base64
from functools import cached_property
from io import BytesIO
import os
import re
import tempfile
from typing import List, Union, Optional, Dict, Any

from huggingface_hub import model_info
from loguru import logger

from leptonai.registry import Registry
from leptonai.photon.base import schema_registry, type_registry
from leptonai.photon import Photon, PNGResponse, FileParam
from .hf_utils import (
    pipeline_registry,
    img_param_to_img,
    hf_missing_package_error_message,
    hf_try_explain_run_exception,
)
from .hf_dependencies import hf_pipeline_dependencies

task_cls_registry = Registry()


SUPPORTED_TASKS = [
    # diffusers
    "text-to-image",
    # transformers
    "audio-classification",
    "automatic-speech-recognition",
    "conversational",
    "depth-estimation",
    "document-question-answering",
    "feature-extraction",
    "fill-mask",
    "image-classification",
    "image-to-text",
    "object-detection",
    "question-answering",
    "sentiment-analysis",
    "summarization",
    "table-question-answering",
    "text-classification",
    "text-generation",
    "text2text-generation",
    "token-classification",
    "translation",
    "video-classification",
    "visual-question-answering",
    "vqa",
    "zero-shot-classification",
    "zero-shot-image-classification",
    "zero-shot-object-detection",
    # sentence-transformers
    "sentence-similarity",
]

# This is a manually maintained list of mappings from model name to
# tasks. Somehow these models are not properly annotated in the Huggingface
# Hub.
_MANUALLY_ANNOTATED_MODEL_TO_TASK = {
    "hf-internal-testing/tiny-stable-diffusion-torch": "text-to-image",
}

schemas = ["hf", "huggingface"]


def _get_transformers_base_types():
    import transformers

    return (transformers.PreTrainedModel, transformers.Pipeline)


def is_transformers_model(model):
    return isinstance(model, _get_transformers_base_types())


class HuggingfacePhoton(Photon):
    photon_type: str = "hf"
    hf_task: str = "undefined (please override this in your derived class)"
    requirement_dependency: Optional[List[str]] = []

    @property
    def _requirement_dependency(self) -> List[str]:
        # First, get the overridden base class requirement_dependency
        deps: List[str] = super()._requirement_dependency
        # Add manually maintained dependencies to the list.
        if self.hf_model in hf_pipeline_dependencies:
            pipeline_specific_deps = hf_pipeline_dependencies[self.hf_model]
            for d in pipeline_specific_deps:
                if d not in deps:
                    deps.append(d)
        return deps

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        task_cls_registry.register(cls.hf_task, cls)

    @classmethod
    def _parse_model_str(cls, model_str):
        model_parts = model_str.split(":")
        if len(model_parts) != 2:
            raise ValueError(
                f'Unsupported Huggingface model: "{model_str}" (can not parse model'
                " name). Huggingface model spec should be in the form of"
                " hf:<model_name>[@<revision>]."
            )
        schema = model_parts[0]
        if schema not in schemas:
            # In theory, this should not happen - the schema should be
            # automatically checked by the photon registry, but we'll check it
            # here just in case.
            raise ValueError(
                f'Unsupported Huggingface model: "{model_str}" (unknown schema:'
                f' "{schema}")'
            )
        hf_model_id = model_parts[1]
        if "@" in hf_model_id:
            hf_model_id, revision = hf_model_id.split("@")
        else:
            revision = None
        mi = model_info(hf_model_id, revision=revision)

        if hf_model_id in _MANUALLY_ANNOTATED_MODEL_TO_TASK:
            hf_task = _MANUALLY_ANNOTATED_MODEL_TO_TASK[hf_model_id]
        else:
            hf_task = mi.pipeline_tag
            if hf_task is None:
                raise AttributeError(
                    f'Unsupported Huggingface model: "{model_str}" (the model did not'
                    " specify a task).\nUsually, this means that the model creator did"
                    " not intend to publish the model as a pipeline, and is only using"
                    " HuggingFace Hub as a storage for the model weights and misc"
                    " files. Thus, it is not possible to run the model automatically."
                    " This is not a bug of Lepton SDK, but rather a limitation of the"
                    " hf ecosystem.\n\nAs a possible solution, you can try to access"
                    " the corresponding model page at"
                    f" https://huggingface.co/{hf_model_id} and see if the model"
                    " creator provided any instructions on how to run the model. You"
                    " can then wrap this model into a custom Photon with relatively"
                    " easy scaffolding. Check out the documentation at"
                    " https://www.lepton.ai/docs/walkthrough/anatomy_of_a_photon for"
                    " more details."
                )

        if hf_task not in SUPPORTED_TASKS:
            raise ValueError(
                f'Unsupported Huggingface model: "{model_str}" (task: {hf_task}). This'
                " task is not supported by LeptonAI SDK yet. If you would like us to"
                " add support for this task type, please let us know by opening an"
                " issue at https://github.com/lepton/leptonai-sdk/issues/new/choose."
            )

        # 8 chars should be enough to identify a commit
        hf_revision = mi.sha[:8]
        model = f"{schema}:{hf_model_id}@{hf_revision}"

        return model, hf_task, hf_model_id, hf_revision

    def __init__(self, name: str, model: str):
        model, hf_task, hf_model_id, hf_revision = self._parse_model_str(model)
        super().__init__(name, model)

        self.hf_model = hf_model_id
        self.hf_revision = hf_revision
        self.hf_task = hf_task

    @property
    def metadata(self):
        res = super().metadata
        res.pop("py_obj")
        res.update(
            {
                "task": self.hf_task,
            }
        )
        return res

    @cached_property
    def pipeline(self):
        pipeline_creator = pipeline_registry.get(self.hf_task)
        if pipeline_creator is None:
            raise ValueError(f"Could not find pipeline creator for {self.hf_task}")
        logger.info(
            f"Creating pipeline for {self.hf_task}(model={self.hf_model},"
            f" revision={self.hf_revision}).\n"
            "HuggingFace download might take a while, please be patient..."
        )
        try:
            pipeline = pipeline_creator(
                task=self.hf_task,
                model=self.hf_model,
                revision=self.hf_revision,
            )
        except ImportError as e:
            # Huggingface has a mechanism that detects dependencies, and then prints dependent
            # libraries in the error message. When this happens, we want to parse the error and
            # then tell the user what they should do.
            # See https://github.com/huggingface/transformers/blob/ce2e7ef3d96afaf592faf3337b7dd997c7ad4928/src/transformers/dynamic_module_utils.py#L178
            # for the source code that prints the error message.
            pattern = (
                "This modeling file requires the following packages that were not found"
                " in your environment: (.*?). Run `pip install"
            )
            match = re.search(pattern, e.msg)
            if match:
                missing_packages = match.group(1).split(", ")
                raise ImportError(
                    hf_missing_package_error_message(self.hf_task, missing_packages)
                ) from e
            else:
                raise e

        return pipeline

    def init(self):
        super().init()
        # access pipeline here to trigger download and load
        self.pipeline

    def run(self, *args, **kwargs):
        import torch

        if torch.cuda.is_available():
            with torch.autocast(device_type="cuda"):
                return self.pipeline(*args, **kwargs)
        else:
            return self.pipeline(*args, **kwargs)

    @classmethod
    def create_from_model_str(cls, name, model_str):
        _, hf_task, _, _ = cls._parse_model_str(model_str)
        task_cls = task_cls_registry.get(hf_task)
        return task_cls(name, model_str)

    @classmethod
    def create_from_model_obj(cls, name, model):
        import transformers

        if not is_transformers_model(model):
            raise ValueError(f"Unsupported model type: {type(model)}")

        try:
            if isinstance(model, transformers.Pipeline):
                model = model.model
            model_name = model.name_or_path
        except AttributeError:
            raise ValueError(
                f'Unsupported Huggingface model: "{model}" (can not find corresponding'
                " model name)"
            )

        try:
            # NOTE: This is a highly private API in transformers.
            # We can not guarantee always possible to extract the
            # revision for sdk usage
            revision = model.config._get_config_dict(model.name_or_path)[0][
                "_commit_hash"
            ]
            model_name = f"{model_name}@{revision}"
        except Exception as e:
            logger.warning(f"Can not get revision for model {model_name}: {e}")
            revision = None

        return cls.create_from_model_str(name, f"hf:{model_name}")

    @classmethod
    def load(cls, photon_file, metadata):
        name = metadata["name"]
        model = metadata["model"]
        return cls.create_from_model_str(name, model)


def _get_generated_text(res):
    if isinstance(res, str):
        return res
    elif isinstance(res, dict):
        return res["generated_text"]
    elif isinstance(res, list):
        if len(res) == 1:
            return _get_generated_text(res[0])
        else:
            return [_get_generated_text(r) for r in res]
    else:
        raise ValueError(f"Unsupported result type in _get_generated_text: {type(res)}")


class HuggingfaceTextGenerationPhoton(HuggingfacePhoton):
    hf_task: str = "text-generation"
    requirement_dependency: Optional[List[str]] = ["ctransformers"]

    @Photon.handler(
        "run",
        example={
            "inputs": "I enjoy walking with my cute dog",
            "max_new_tokens": 50,
            "do_sample": True,
            "top_k": 50,
            "top_p": 0.95,
        },
    )
    def run_handler(
        self,
        inputs: Union[str, List[str]],
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        temperature: Optional[float] = 1.0,
        repetition_penalty: Optional[float] = None,
        max_new_tokens: Optional[int] = None,
        max_time: Optional[float] = None,
        return_full_text: bool = True,
        num_return_sequences: int = 1,
        do_sample: bool = True,
        **kwargs,
    ) -> Union[str, List[str]]:
        try:
            res = self.run(
                inputs,
                top_k=top_k,
                top_p=top_p,
                temperature=temperature,
                repetition_penalty=repetition_penalty,
                max_new_tokens=max_new_tokens,
                max_time=max_time,
                return_full_text=return_full_text,
                num_return_sequences=num_return_sequences,
                do_sample=do_sample,
                **kwargs,
            )
            return _get_generated_text(res)
        except Exception as e:
            raise hf_try_explain_run_exception(e)

    def answer(self, question, history):
        history.append({"role": "user", "content": question})

        # TODO: should limit the number of history messages to include into the
        # prompt so that it doesn't exceed the max context length of the model
        history_prompt = os.linesep.join(
            [f"{h['role']}: {h['content']}" for h in history]
        )
        prompt = f"""\
The following is a friendly conversation between a user and an assistant. The assistant is talkative and provides lots of specific details from its context. If the assistant does not know the answer to a question, it truthfully says it does not know.
Current conversation:
{history_prompt}

assistant:
"""
        response = self.run(prompt, return_full_text=False)[0]["generated_text"]
        history.append({"role": "assistant", "content": response})
        messages = [
            (history[i]["content"], history[i + 1]["content"])
            for i in range(0, len(history) - 1, 2)
        ]
        return messages, history

    @Photon.handler(mount=True)
    def ui(self):
        import gradio as gr

        blocks = gr.Blocks()
        with blocks:
            chatbot = gr.Chatbot(label=f"Chatbot ({self.hf_model})")
            state = gr.State([])
            with gr.Row():
                txt = gr.Textbox(
                    show_label=False, placeholder="Enter text and press enter"
                )
            txt.submit(self.answer, [txt, state], [chatbot, state])
        return blocks


class HuggingfaceText2TextGenerationPhoton(HuggingfacePhoton):
    # essentially Text-generation task, but uses Encoder-Decoder architecture
    hf_task: str = "text2text-generation"
    requirement_dependency: Optional[List[str]] = ["protobuf==3.20.*"]

    @Photon.handler(
        "run",
        example={
            "inputs": "I enjoy walking with my cute dog",
            "max_new_tokens": 50,
            "do_sample": True,
            "top_k": 50,
            "top_p": 0.95,
        },
    )
    def run_handler(
        self,
        inputs: Union[str, List[str]],
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        temperature: Optional[float] = 1.0,
        repetition_penalty: Optional[float] = None,
        max_new_tokens: Optional[int] = None,
        max_time: Optional[float] = None,
        num_return_sequences: int = 1,
        do_sample: bool = True,
        **kwargs,
    ) -> Union[str, List[str]]:
        res = self.run(
            inputs,
            top_k=top_k,
            top_p=top_p,
            temperature=temperature,
            repetition_penalty=repetition_penalty,
            max_new_tokens=max_new_tokens,
            max_time=max_time,
            num_return_sequences=num_return_sequences,
            do_sample=do_sample,
            **kwargs,
        )
        return _get_generated_text(res)

    def answer(self, question, history):
        history.append({"role": "user", "content": question})

        # TODO: should limit the number of history messages to include into the
        # prompt so that it doesn't exceed the max context length of the model
        history_prompt = os.linesep.join(
            [f"{h['role']}: {h['content']}" for h in history]
        )
        prompt = f"""\
The following is a friendly conversation between a user and an assistant. The assistant is talkative and provides lots of specific details from its context. If the assistant does not know the answer to a question, it truthfully says it does not know.
Current conversation:
{history_prompt}

assistant:
"""
        response = self.run(prompt)[0]["generated_text"]
        history.append({"role": "assistant", "content": response})
        messages = [
            (history[i]["content"], history[i + 1]["content"])
            for i in range(0, len(history) - 1, 2)
        ]
        return messages, history

    @Photon.handler(mount=True)
    def ui(self):
        import gradio as gr

        blocks = gr.Blocks()
        with blocks:
            chatbot = gr.Chatbot(label=f"Chatbot ({self.hf_model})")
            state = gr.State([])
            with gr.Row():
                txt = gr.Textbox(
                    show_label=False, placeholder="Enter text and press enter"
                )
            txt.submit(self.answer, [txt, state], [chatbot, state])
        return blocks


class HuggingfaceASRPhoton(HuggingfacePhoton):
    hf_task: str = "automatic-speech-recognition"

    system_dependency = ["ffmpeg"]

    @Photon.handler(
        "run",
        example={
            "inputs": (
                "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/1.flac"
            )
        },
    )
    def run_handler(self, inputs: Union[str, FileParam]) -> str:
        if isinstance(inputs, FileParam):
            file = tempfile.NamedTemporaryFile()
            with open(file.name, "wb") as f:
                f.write(inputs.file.read())
                f.flush()
            inputs = file.name

        res = self.run(inputs)
        return res["text"]


class HuggingfaceTextToImagePhoton(HuggingfacePhoton):
    hf_task: str = "text-to-image"

    def init(self):
        super().init()

        import torch

        if torch.cuda.is_available():
            self._device = "cuda"
        else:
            self._device = "cpu"

    @Photon.handler(
        "run",
        example={
            "prompt": "a photograph of an astronaut riding a horse",
            "num_inference_steps": 25,
            "seed": 42,
        },
    )
    def run_handler(
        self,
        prompt: Union[str, List[str]],
        height: Optional[int] = None,
        width: Optional[int] = None,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        negative_prompt: Optional[Union[str, List[str]]] = None,
        seed: Optional[Union[int, List[int]]] = None,
        **kwargs,
    ) -> PNGResponse:
        import torch

        if seed is not None:
            if not isinstance(seed, list):
                seed = [seed]
            generator = [
                torch.Generator(device=self._device).manual_seed(s) for s in seed
            ]
        else:
            generator = None

        res = self.run(
            prompt,
            height=height,
            width=width,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            negative_prompt=negative_prompt,
            generator=generator,
            **kwargs,
        )
        img_io = BytesIO()
        res.images[0].save(img_io, format="PNG", quality="keep")
        img_io.seek(0)
        return PNGResponse(img_io)


class HuggingfaceSummarizationPhoton(HuggingfacePhoton):
    hf_task: str = "summarization"

    @Photon.handler(
        "run",
        example={
            "inputs": """The tower is 324 metres (1,063 ft) tall, about the same height as an 81-storey building, and the tallest structure in Paris. Its base is square, measuring 125 metres (410 ft) on each side. During its construction, the Eiffel Tower surpassed the Washington Monument to become the tallest man-made structure in the world, a title it held for 41 years until the Chrysler Building in New York City was finished in 1930. It was the first structure to reach a height of 300 metres. Due to the addition of a broadcasting aerial at the top of the tower in 1957, it is now taller than the Chrysler Building by 5.2 metres (17 ft). Excluding transmitters, the Eiffel Tower is the second tallest free-standing structure in France after the Millau Viaduct."""
        },
    )
    def run_handler(
        self,
        inputs: Union[str, List[str]],
        **kwargs,
    ) -> Union[str, List[str]]:
        res = self.run(
            inputs,
            **kwargs,
        )
        if isinstance(res, dict):
            return res["summary_text"]
        elif len(res) == 1:
            return res[0]["summary_text"]
        else:
            return [r["summary_text"] for r in res]

    def summarize(self, text: str) -> str:
        return self.run_handler(text)

    @Photon.handler(mount=True)
    def ui(self):
        import gradio as gr

        blocks = gr.Blocks()
        with blocks:
            gr.Markdown("""
            # Summarize
            Start typing below to see the output.
            """)
            input_box = gr.Textbox(placeholder="text to summarize")
            output_box = gr.Textbox()
            btn = gr.Button("Summarize")
            btn.click(fn=self.summarize, inputs=input_box, outputs=output_box)

        return blocks


class HuggingfaceSentenceSimilarityPhoton(HuggingfacePhoton):
    hf_task: str = "sentence-similarity"

    @Photon.handler(example={"inputs": "The cat sat on the mat"})
    def embed(
        self,
        inputs: Union[str, List[str]],
        **kwargs,
    ) -> Union[List[float], List[List[float]]]:
        res = self.run(
            inputs,
            **kwargs,
        )
        if isinstance(res, list):
            return [r.tolist() for r in res]
        else:
            return res.tolist()

    @Photon.handler(
        "run",
        example={
            "source_sentence": "That is a happy person",
            "sentences": [
                "That is a happy dog",
                "That is a very happy person",
                "Today is a sunny day",
            ],
        },
    )
    def run_handler(
        self,
        source_sentence: str,
        sentences: Union[str, List[str]],
        **kwargs,
    ) -> Union[float, List[float]]:
        from sentence_transformers import util

        sentences_embs = self.run(sentences, **kwargs)
        source_sentence_emb = self.run(source_sentence, **kwargs)
        res = util.cos_sim(source_sentence_emb, sentences_embs)

        if res.dim() != 2 or res.size(0) != 1:
            logger.error(f"Unexpected result shape: {res.shape}")
        return res[0].tolist()


class HuggingfaceSentimentAnalysisPhoton(HuggingfacePhoton):
    hf_task: str = "sentiment-analysis"

    @Photon.handler(example={"inputs": ["I love you", "I hate you"]})
    def run_handler(
        self,
        inputs: Union[str, List[str]],
        **kwargs,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        res = self.run(
            inputs,
            **kwargs,
        )
        return res


# text-classification is an alias of sentiment-analysis
class HuggingfaceTextClassificationPhoton(HuggingfaceSentimentAnalysisPhoton):
    hf_task: str = "text-classification"


class HuggingfaceAudioClassificationPhoton(HuggingfacePhoton):
    hf_task: str = "audio-classification"

    system_dependency = ["ffmpeg"]

    @Photon.handler(
        "run",
        example={
            "inputs": (
                "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/1.flac"
            )
        },
    )
    def run_handler(
        self,
        inputs: Union[Union[str, FileParam], List[Union[str, FileParam]]],
        **kwargs,
    ) -> Union[
        List[Dict[str, Union[float, str]]], List[List[Dict[str, Union[float, str]]]]
    ]:
        inputs_is_list = isinstance(inputs, list)
        if not inputs_is_list:
            inputs = [inputs]
        inputs_ = []
        # keep references to NamedTemporaryFile objects so they don't get deleted
        temp_files = []
        for inp in inputs:
            if isinstance(inp, FileParam):
                file = tempfile.NamedTemporaryFile()
                with open(file.name, "wb") as f:
                    f.write(inp.file.read())
                    f.flush()
                temp_files.append(file)
                inputs_.append(file.name)
            else:
                inputs_.append(inp)
        res = self.run(
            inputs_,
            **kwargs,
        )
        if not inputs_is_list:
            res = res[0]
        return res


class HuggingfaceDepthEstimationPhoton(HuggingfacePhoton):
    hf_task: str = "depth-estimation"

    @Photon.handler(
        "run",
        example={
            "images": [
                "http://images.cocodataset.org/val2017/000000039769.jpg",
                "https://images.unsplash.com/photo-1536396123481-991b5b636cbb?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2896&q=80",
            ]
        },
    )
    def run_handler(
        self,
        images: Union[Union[str, FileParam], List[Union[str, FileParam]]],
        **kwargs,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        inputs_is_list = isinstance(images, list)

        if not inputs_is_list:
            images = [images]
        images = [img_param_to_img(img) for img in images]

        res = self.run(
            images,
            **kwargs,
        )

        if not isinstance(res, list):
            res = [res]
        for i, r in enumerate(res):
            # TODO: Should we drop "predicted_depth" in the response?
            # Convert "predicted_depth" (torch.Tensor) to list(s) of floats
            predicted_depth = r["predicted_depth"].tolist()

            # Convert "depth" PIL.Image to base64-encoded JPEG
            depth_io = BytesIO()
            r["depth"].save(depth_io, format="JPEG")
            depth = base64.b64encode(depth_io.getvalue()).decode("ascii")

            res[i] = {
                "predicted_depth": predicted_depth,
                "depth": depth,
            }

        if not inputs_is_list:
            res = res[0]
        return res

    @Photon.handler(mount=True)
    def ui(self):
        import gradio as gr

        blocks = gr.Blocks()
        with blocks:
            with gr.Row():
                input_image = gr.Image(type="filepath")
                output_image = gr.Image(type="pil")
            with gr.Row():
                btn = gr.Button("Depth Estimate", variant="primary")
                btn.click(
                    fn=lambda img: self.run(img)["depth"],
                    inputs=input_image,
                    outputs=output_image,
                )
        return blocks


class HuggingfaceImageToTextPhoton(HuggingfacePhoton):
    hf_task: str = "image-to-text"

    @Photon.handler(
        "run",
        example={"images": "http://images.cocodataset.org/val2017/000000039769.jpg"},
    )
    def run_handler(
        self,
        images: Union[Union[str, FileParam], List[Union[str, FileParam]]],
        **kwargs,
    ) -> Union[str, List[str]]:
        images_is_list = isinstance(images, list)
        if not images_is_list:
            images = [images]
        images_ = []
        # keep references to NamedTemporaryFile objects so they don't get deleted
        temp_files = []
        for img in images:
            if isinstance(img, FileParam):
                file = tempfile.NamedTemporaryFile()
                with open(file.name, "wb") as f:
                    f.write(img.file.read())
                    f.flush()
                temp_files.append(file)
                images_.append(file.name)
            else:
                images_.append(img)
        res = self.run(
            images_,
            **kwargs,
        )
        return _get_generated_text(res)


def register_hf_photon():
    schema_registry.register(schemas, HuggingfacePhoton.create_from_model_str)
    type_registry.register(
        is_transformers_model, HuggingfacePhoton.create_from_model_obj
    )
