from collections import namedtuple
import httpx
import os

from leptonai.config import BASE_IMAGE_REPO, DEFAULT_PORT
from leptonai.photon import Photon


class Server(Photon):
    image: f"{BASE_IMAGE_REPO}:tuna-23.02"

    def _init_ft_worker(self):
        import fastchat.serve.ft_worker

        worker = fastchat.serve.ft_worker.ModelWorker(
            controller_addr=None,
            worker_addr=None,
            worker_id=fastchat.serve.ft_worker.worker_id,
            no_register=True,
            model_path=os.environ.get("MODEL_PATH", "./model"),
            model_names=[
                "gpt-3.5-turbo",
                "text-davinci-003",
                "text-embedding-ada-002",
            ],
            device="cuda",
            num_gpus=1,
            use_int=os.getenv("USE_INT", "False").lower() in ("true", "1", "t"),
        )
        FakeArgs = namedtuple("Args", ["limit_model_concurrency"])
        fastchat.serve.ft_worker.args = FakeArgs(limit_model_concurrency=5)
        fastchat.serve.ft_worker.worker = worker

    @staticmethod
    async def _patch_get_worker_address(
        model_name: str, client: httpx.AsyncClient
    ) -> str:
        # TODO: makes port configurable
        return f"http://localhost:{DEFAULT_PORT}/worker"

    @staticmethod
    async def _patch_show_available_models():
        import fastchat.serve.ft_worker
        from fastchat.protocol.openai_api_protocol import (
            ModelCard,
            ModelList,
            ModelPermission,
        )

        models = []
        worker_status = fastchat.serve.ft_worker.worker.get_status()
        for name in sorted(worker_status["model_names"]):
            models.append(ModelCard(id=name, root=name, permission=[ModelPermission()]))
        return ModelList(data=models)

    def _init_openai_api_server(self):
        import fastchat.serve.openai_api_server

        fastchat.serve.openai_api_server.app_settings.controller_address = None
        fastchat.serve.openai_api_server.app_settings.api_keys = None
        fastchat.serve.openai_api_server._get_worker_address = (
            self._patch_get_worker_address
        )
        for i, route in enumerate(fastchat.serve.openai_api_server.app.routes):
            if route.path == "/v1/models":
                fastchat.serve.openai_api_server.app.routes.pop(i)
                break
        fastchat.serve.openai_api_server.app.get("/v1/models")(
            self._patch_show_available_models
        )

    def init(self):
        self._init_ft_worker()
        self._init_openai_api_server()

    @Photon.handler(path="worker", mount=True)
    def ft_worker_subapp(self):
        import fastchat.serve.ft_worker

        return fastchat.serve.ft_worker.app

    @Photon.handler(path="api", mount=True)
    def openai_api_server_subapp(self):
        import fastchat.serve.openai_api_server

        return fastchat.serve.openai_api_server.app
