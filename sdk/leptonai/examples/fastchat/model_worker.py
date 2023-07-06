from collections import namedtuple
import os

from leptonai.photon import Photon

import fastchat.serve.model_worker


class Server(Photon):
    requirement_dependency = [
        "git+https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/leptonai/FastChat.git@2f18851"
    ]

    def init(self):
        worker = fastchat.serve.model_worker.ModelWorker(
            controller_addr=os.environ.get("CONTROLLER_ADDR", "http://0.0.0.0:21001"),
            worker_addr=os.environ.get("WORKER_ADDR", "http://0.0.0.0:21002"),
            worker_id=fastchat.serve.model_worker.worker_id,
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
            max_gpu_memory=None,
            load_8bit=False,
            cpu_offloading=False,
            gptq_config=None,
        )
        FakeArgs = namedtuple("Args", ["limit_model_concurrency", "stream_interval"])
        fastchat.serve.model_worker.args = FakeArgs(
            limit_model_concurrency=5, stream_interval=2
        )
        fastchat.serve.model_worker.worker = worker

    @Photon.handler(path="", mount=True)
    def subapp(self):
        return fastchat.serve.model_worker.app
