from leptonai.config import BASE_IMAGE_REPO
from leptonai.photon import Photon

import fastchat.serve.controller


class Server(Photon):
    image: f"{BASE_IMAGE_REPO}:tuna-runner-0.1.9"

    def init(self):
        controller = fastchat.serve.controller.Controller("shortest_queue")
        fastchat.serve.controller.controller = controller

    @Photon.handler(path="", mount=True)
    def subapp(self):
        return fastchat.serve.controller.app
