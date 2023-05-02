from huggingface_hub import model_info
from loguru import logger
import transformers

from .base import Photon, schema_registry, type_registry

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


class HuggingfacePhoton(Photon):
    def __init__(self, name: str, model: str):
        model_parts = model.split(":")
        if len(model_parts) != 2:
            raise ValueError(
                f'Unsupported Huggingface model: "{model}" (can not parse model name)'
            )
        schema = model_parts[0]
        if schema not in schemas:
            raise ValueError(
                f'Unsupported Huggingface model: "{model}" (unknown schema: "{schema}")'
            )
        hf_model_id = model_parts[1]
        if "@" in hf_model_id:
            hf_model_id, revision = hf_model_id.split("@")
        else:
            revision = None
        mi = model_info(hf_model_id, revision=revision)

        try:
            task = mi.pipeline_tag
        except AttributeError:
            raise ValueError(
                f'Unsupported Huggingface model: "{model}" (can not find corresponding task)'
            )
        if task not in SUPPORTED_TASKS:
            raise ValueError(
                f'Unsupported Huggingface model: "{model}" (task: "{task}")'
            )

        # 8 chars should be enough to identify a commit
        hf_revision = mi.sha[:8]
        model = f"{schema}:{hf_model_id}@{hf_revision}"
        super().__init__(name, model)

        self.hf_task = task
        self.hf_model = hf_model_id
        self.hf_revision = hf_revision

        self._in_process_runner = None

    @property
    def metadata(self):
        from .hf_runner import HuggingfaceServerRunner

        res = super().metadata
        res.update(
            {
                "task": self.hf_task,
                "image": HuggingfaceServerRunner.image,
                "args": HuggingfaceServerRunner.args,
            }
        )
        return res

    def run(self, *args, **kwargs):
        from .hf_runner import HuggingfaceInProcessRunner

        if self._in_process_runner is None:
            self._in_process_runner = HuggingfaceInProcessRunner(self)
        return self._in_process_runner.run(*args, **kwargs)

    def run_as_server(self, port: int = 8080):
        from .hf_runner import HuggingfaceServerRunner

        return HuggingfaceServerRunner(self, port).run()

    @classmethod
    def create_from_model(cls, name, model):
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

        return cls(name, f"hf:{model_name}")


schema_registry.register(schemas, HuggingfacePhoton)
type_registry.register(transformers_types, HuggingfacePhoton.create_from_model)
