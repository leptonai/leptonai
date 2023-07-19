from leptonai.photon import Photon

import fastchat.serve.controller


class Server(Photon):
    requirement_dependency = [
        "git+https://github.com/lm-sys/FastChat.git@974537e",
    ]

    def init(self):
        controller = fastchat.serve.controller.Controller("shortest_queue")
        fastchat.serve.controller.controller = controller

    @Photon.handler(path="", mount=True)
    def subapp(self):
        return fastchat.serve.controller.app
