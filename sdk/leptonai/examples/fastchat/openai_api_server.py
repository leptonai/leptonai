import os

from leptonai.photon import Photon

import fastchat.serve.openai_api_server


class Server(Photon):
    requirement_dependency = ["git+https://github.com/leptonai/FastChat.git@2f18851"]

    def init(self):
        fastchat.serve.openai_api_server.app_settings.controller_address = (
            os.environ.get("CONTROLLER_ADDR", "http://0.0.0.0:21001")
        )
        fastchat.serve.openai_api_server.app_settings.api_keys = None

    @Photon.handler(path="", mount=True)
    def subapp(self):
        return fastchat.serve.openai_api_server.app
