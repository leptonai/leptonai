import asyncio
import os

from leptonai.photon import Photon
from leptonai.config import TRUST_REMOTE_CODE


class vLLM(Photon):
    requirement_dependency = [
        "vllm>=0.2.0",
        "fschat",
    ]

    def init(self):
        from vllm.entrypoints.openai import api_server
        from vllm.engine.arg_utils import AsyncEngineArgs
        from vllm.engine.async_llm_engine import AsyncLLMEngine
        from vllm.transformers_utils.tokenizer import get_tokenizer

        if "MODEL" not in os.environ:
            raise ValueError(
                "Please set the 'MODEL' environment variable to specify the model to"
                " use (e.g. codellama/CodeLlama-7b-Instruct-hf)"
            )
        model = os.environ["MODEL"]
        engine_args = AsyncEngineArgs(
            model=model,
            trust_remote_code=os.environ.get("TRUST_REMOTE_CODE", TRUST_REMOTE_CODE),
        )
        engine = AsyncLLMEngine.from_engine_args(engine_args)
        engine_model_config = asyncio.run(engine.get_model_config())
        max_model_len = engine_model_config.max_model_len

        api_server.served_model = os.environ.get("MODEL_NAME", model)
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
