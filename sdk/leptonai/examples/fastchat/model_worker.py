from collections import namedtuple

from leptonai.photon import Photon

import fastchat.serve.model_worker


class Server(Photon):
    requirement_dependency = ["https://github.com/leptonai/FastChat.git@d426b61"]

    def init(self):
        worker = fastchat.serve.model_worker.ModelWorker(
            controller_addr="http://0.0.0.0:21001",
            worker_addr="http://0.0.0.0:21002",
            worker_id=fastchat.serve.model_worker.worker_id,
            no_register=False,
            model_path="./model",
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
