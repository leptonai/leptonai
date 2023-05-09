from abc import abstractmethod
from typing import List, Union, Optional

from backports.cached_property import cached_property
import numpy as np
from huggingface_hub import model_info
from loguru import logger
import transformers

from fastapi.responses import StreamingResponse

from lepton.registry import Registry
from .base import schema_registry, type_registry
from .runner import RunnerPhoton, handler, send_pil_img
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
transformers_types = (transformers.PreTrainedModel, transformers.Pipeline)


class HuggingfacePhoton(RunnerPhoton):
    photon_type: str = "hf"

    image: str = "lepton:photon-hf-runner"
    args: list = ["--shm-size=1g"]

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

    @property
    def metadata(self):
        res = super().metadata
        res.pop("py_obj")
        res.update(
            {
                "task": self.hf_task,
                "image": self.image,
                "args": self.args,
            }
        )
        return res

    @property
    def extra_files(self):
        res = super().extra_files
        res.pop(self.obj_pkl_filename)
        return res

    @cached_property
    def pipeline(self):
        pipeline_creator = pipeline_registry.get(self.hf_task)
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
        if not isinstance(model, transformers_types):
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
            # We can not gurantee always possible to extract the
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
type_registry.register(transformers_types, HuggingfacePhoton.create_from_model_obj)


class HuggingfaceTextGenerationPhoton(HuggingfacePhoton):
    hf_task: str = "text-generation"

    @handler("run")
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
        )
        if len(res) == 1:
            return res[0]["generated_text"]
        else:
            return [r["generated_text"] for r in res]


class HuggingfaceASRPhoton(HuggingfacePhoton):
    hf_task: str = "automatic-speech-recognition"

    @handler("run")
    def run_handler(self, inputs: str) -> str:
        res = self.run(inputs)
        return res["text"]


class HuggingfaceTextToImagePhoton(HuggingfacePhoton):
    hf_task: str = "text-to-image"

    @handler("run", response_class=StreamingResponse)
    def run_handler(
        self,
        prompt: str,
        height: Optional[int] = None,
        width: Optional[int] = None,
        num_inference_steps: int = 50,
        **kwargs,
    ):
        res = self.run(
            prompt,
            height=height,
            width=width,
            num_inference_steps=num_inference_steps,
            **kwargs,
        )
        return send_pil_img(res.images[0])
