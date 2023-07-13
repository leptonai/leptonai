import os

from leptonai.config import BASE_IMAGE_REPO, BASE_IMAGE_VERSION
from leptonai.photon import Photon

import fastchat.serve.openai_api_server


class Server(Photon):
    image: f"{BASE_IMAGE_REPO}:tuna-runner-{BASE_IMAGE_VERSION}"

    def init(self):
        fastchat.serve.openai_api_server.app_settings.controller_address = (
            os.environ.get("CONTROLLER_ADDR", "http://0.0.0.0:21001")
        )
        fastchat.serve.openai_api_server.app_settings.api_keys = None

    @Photon.handler(path="api", mount=True)
    def subapp(self):
        return fastchat.serve.openai_api_server.app
