from collections import namedtuple
import os

from leptonai.config import BASE_IMAGE_REPO, BASE_IMAGE_VERSION
from leptonai.photon import Photon

import fastchat.serve.ft_worker


class Server(Photon):
    image: f"{BASE_IMAGE_REPO}:tuna-runner-{BASE_IMAGE_VERSION}"

    def init(self):
        worker = fastchat.serve.ft_worker.ModelWorker(
            controller_addr=os.environ.get("CONTROLLER_ADDR", "http://0.0.0.0:21001"),
            worker_addr=os.environ.get("WORKER_ADDR", "http://0.0.0.0:21002"),
            worker_id=fastchat.serve.ft_worker.worker_id,
            no_register=False,
            model_path=os.environ.get("MODEL_PATH", "./model"),
            model_names=[
                "tuna",
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

    @Photon.handler(path="", mount=True)
    def subapp(self):
        return fastchat.serve.ft_worker.app
