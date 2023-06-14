from io import BytesIO
import os
from typing import List, Union, Optional

from backports.cached_property import cached_property
from huggingface_hub import model_info
from loguru import logger

from leptonai.registry import Registry
from .base import schema_registry, type_registry
from .runner import RunnerPhoton, handler, PNGResponse
from .hf_runner import pipeline_registry

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

schemas = ["hf", "huggingface"]


def _get_transformers_base_types():
    import transformers

    return (transformers.PreTrainedModel, transformers.Pipeline)


def is_transformers_model(model):
    return isinstance(model, _get_transformers_base_types())


class HuggingfacePhoton(RunnerPhoton):
    photon_type: str = "hf"
    requirement_dependency: Optional[List[str]] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        task_cls_registry.register(cls.hf_task, cls)

    @classmethod
    def _parse_model_str(cls, model_str):
        model_parts = model_str.split(":")
        if len(model_parts) != 2:
            raise ValueError(
                f'Unsupported Huggingface model: "{model_str}" (can not parse model name)'
            )
        schema = model_parts[0]
        if schema not in schemas:
            raise ValueError(
                f'Unsupported Huggingface model: "{model_str}" (unknown schema: "{schema}")'
            )
        hf_model_id = model_parts[1]
        if "@" in hf_model_id:
            hf_model_id, revision = hf_model_id.split("@")
        else:
            revision = None
        mi = model_info(hf_model_id, revision=revision)

        try:
            hf_task = mi.pipeline_tag
        except AttributeError:
            raise ValueError(
                f'Unsupported Huggingface model: "{model_str}" (can not find corresponding task)'
            )
        if hf_task not in SUPPORTED_TASKS:
            raise ValueError(
                f'Unsupported Huggingface model: "{model_str}" (task: "{hf_task}")'
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

    @property
    def _extra_files(self):
        res = super()._extra_files
        res.pop(self.obj_pkl_filename)
        return res

    @cached_property
    def pipeline(self):
        pipeline_creator = pipeline_registry.get(self.hf_task)
        if pipeline_creator is None:
            raise ValueError(f"Could not find pipeline creator for {self.hf_task}")
        logger.info(
            f"Creating pipeline for {self.hf_task}(model={self.hf_model}, revision={self.hf_revision})"
        )
        pipeline = pipeline_creator(
            task=self.hf_task,
            model=self.hf_model,
            revision=self.hf_revision,
        )
        return pipeline

    def run(self, *args, **kwargs):
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
                f'Unsupported Huggingface model: "{model}" (can not find corresponding model name)'
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


schema_registry.register(schemas, HuggingfacePhoton.create_from_model_str)
type_registry.register(is_transformers_model, HuggingfacePhoton.create_from_model_obj)


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

    @handler(
        "run",
        example={
            "inputs": "I enjoy walking with my cute dog",
            "max_length": 50,
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

    @handler(mount=True)
    def ui(self):
        import gradio as gr

        blocks = gr.Blocks()
        with blocks:
            chatbot = gr.Chatbot(label=f"Chatbot ({self.hf_model})")
            state = gr.State([])
            with gr.Row():
                txt = gr.Textbox(
                    show_label=False, placeholder="Enter text and press enter"
                ).style(container=False)
            txt.submit(self.answer, [txt, state], [chatbot, state])
        return blocks


class HuggingfaceText2TextGenerationPhoton(HuggingfacePhoton):
    # essentially Text-generation task, but uses Encoder-Decoder architecture
    hf_task: str = "text2text-generation"
    requirement_dependency: Optional[List[str]] = ["protobuf==3.20.*"]

    @handler(
        "run",
        example={
            "inputs": "I enjoy walking with my cute dog",
            "max_length": 50,
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

    @handler(mount=True)
    def ui(self):
        import gradio as gr

        blocks = gr.Blocks()
        with blocks:
            chatbot = gr.Chatbot(label=f"Chatbot ({self.hf_model})")
            state = gr.State([])
            with gr.Row():
                txt = gr.Textbox(
                    show_label=False, placeholder="Enter text and press enter"
                ).style(container=False)
            txt.submit(self.answer, [txt, state], [chatbot, state])
        return blocks


class HuggingfaceASRPhoton(HuggingfacePhoton):
    hf_task: str = "automatic-speech-recognition"

    @handler(
        "run",
        example={
            "inputs": "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/1.flac"
        },
    )
    def run_handler(self, inputs: str) -> str:
        res = self.run(inputs)
        return res["text"]


class HuggingfaceTextToImagePhoton(HuggingfacePhoton):
    hf_task: str = "text-to-image"

    @handler(
        "run",
        example={
            "prompt": "a photograph of an astronaut riding a horse",
            "num_inference_steps": 25,
        },
    )
    def run_handler(
        self,
        prompt: str,
        height: Optional[int] = None,
        width: Optional[int] = None,
        num_inference_steps: int = 50,
        **kwargs,
    ) -> PNGResponse:
        res = self.run(
            prompt,
            height=height,
            width=width,
            num_inference_steps=num_inference_steps,
            **kwargs,
        )
        img_io = BytesIO()
        res.images[0].save(img_io, format="PNG", quality="keep")
        img_io.seek(0)
        return PNGResponse(img_io)


class HuggingfaceSummarizationPhoton(HuggingfacePhoton):
    hf_task: str = "summarization"

    @handler(
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

    @handler(mount=True)
    def ui(self):
        import gradio as gr

        blocks = gr.Blocks()
        with blocks:
            gr.Markdown(
                """
            # Summarize
            Start typing below to see the output.
            """
            )
            input_box = gr.Textbox(placeholder="text to summarize")
            output_box = gr.Textbox()
            btn = gr.Button("Summarize")
            btn.click(fn=self.summarize, inputs=input_box, outputs=output_box)

        return blocks


class HuggingfaceSentenceSimilarityPhoton(HuggingfacePhoton):
    hf_task: str = "sentence-similarity"

    @handler(example={"inputs": "The cat sat on the mat"})
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

    @handler(
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
