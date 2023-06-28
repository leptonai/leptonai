from collections import namedtuple

from leptonai.photon import Photon

import fastchat.serve.gradio_web_server


class Server(Photon):
    requirement_dependency = ["https://github.com/leptonai/FastChat.git@d426b61"]

    def init(self):
        fastchat.serve.gradio_web_server.controller_url = "http://0.0.0.0:21001"
        fastchat.serve.gradio_web_server.enable_moderation = False
        fastchat.serve.gradio_web_server.templates_map.clear()

        (
            self._models,
            fastchat.serve.gradio_web_server.templates_map,
        ) = fastchat.serve.gradio_web_server.get_model_list(
            fastchat.serve.gradio_web_server.controller_url
        )

        FakeArgs = namedtuple("Args", ["model_list_mode"])
        fastchat.serve.gradio_web_server.args = FakeArgs(model_list_mode="reload")

    @Photon.handler(path="", mount=True)
    def subapp(self):
        demo = fastchat.serve.gradio_web_server.build_demo(self._models)
        return demo.queue(concurrency_count=10, status_update_rate=10, api_open=False)
