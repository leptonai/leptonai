import asyncio
import os

from loguru import logger

from leptonai.photon import Photon
from leptonai.config import TRUST_REMOTE_CODE
from leptonai.photon.base import schema_registry

VLLM_SCHEMAS = ["vllm"]


class vLLMPhoton(Photon):
    photon_type: str = "vllm"

    deployment_template = {
        # At least using gpu.a10.
        "resource_shape": "gpu.a10",
        "env": {
            "VLLM_MODEL": "",
        },
    }

    requirement_dependency = [
        "vllm>=0.2.0",
        "fschat",
    ]

    def __init__(self, name, model):
        super().__init__(name, model)
        if ":" in model:
            schema, model_id = model.split(":")
        else:
            schema = model
            model_id = ""

        if schema not in VLLM_SCHEMAS:
            raise ValueError(
                f'Unsupported vLLM model: "{model}" (unknown schema: "{schema}")'
            )
        self.model_id = model_id

    @property
    def metadata(self):
        res = super().metadata
        res.pop("py_obj")
        return res

    @classmethod
    def load(cls, photon_file, metadata):
        name = metadata["name"]
        model = metadata["model"]
        return cls(name, model)

    def init(self):
        from vllm.entrypoints.openai import api_server
        from vllm.engine.arg_utils import AsyncEngineArgs
        from vllm.engine.async_llm_engine import AsyncLLMEngine
        from vllm.transformers_utils.tokenizer import get_tokenizer
        import torch

        if os.environ["VLLM_MODEL"] != "":
            # If we specified VLLM_MODEL, always override.
            self.model_id = os.environ["VLLM_MODEL"]
            logger.debug(
                f"Overriding model id with VLLM_MODEL: {self.model_id}."
            )
        if not self.model_id:
            raise RuntimeError(
                "You did not specify a model id. Either do it at photon construction "
                "time with -m vllm:<model_string>, or at runtime with the env "
                "variable VLLM_MODEL."
            )

        if not torch.cuda.is_available():
            raise RuntimeError("vLLM Photon requires CUDA runtime")

        engine_args = AsyncEngineArgs(
            model=self.model_id,
            trust_remote_code=TRUST_REMOTE_CODE,
        )
        engine = AsyncLLMEngine.from_engine_args(engine_args)
        engine_model_config = asyncio.run(engine.get_model_config())
        max_model_len = engine_model_config.max_model_len

        api_server.served_model = self.model_id
        api_server.engine = engine
        api_server.max_model_len = max_model_len
        api_server.tokenizer = get_tokenizer(
            engine_args.tokenizer,
            tokenizer_mode=engine_args.tokenizer_mode,
            trust_remote_code=engine_args.trust_remote_code,
        )

    @Photon.handler(mount=True)
    def api(self):
        from vllm.entrypoints.openai import api_server

        return api_server.app


def register_vllm_photon():
    schema_registry.register(VLLM_SCHEMAS, vLLMPhoton)
