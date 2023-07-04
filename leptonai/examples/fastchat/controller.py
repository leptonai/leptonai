from leptonai.photon import Photon

import fastchat.serve.controller


class Server(Photon):
    requirement_dependency = ["git+https://github.com/leptonai/FastChat.git@2f18851"]

    def init(self):
        controller = fastchat.serve.controller.Controller("shortest_queue")
        fastchat.serve.controller.controller = controller

    @Photon.handler(path="", mount=True)
    def subapp(self):
        return fastchat.serve.controller.app
