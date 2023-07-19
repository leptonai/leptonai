from leptonai.config import BASE_IMAGE_REPO, BASE_IMAGE_VERSION
from leptonai.photon import Photon

import fastchat.serve.controller


class Server(Photon):
    image: f"{BASE_IMAGE_REPO}:tuna-runner-{BASE_IMAGE_VERSION}"

    def init(self):
        controller = fastchat.serve.controller.Controller("shortest_queue")
        fastchat.serve.controller.controller = controller

    @Photon.handler(path="", mount=True)
    def subapp(self):
        return fastchat.serve.controller.app
