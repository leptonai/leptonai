from leptonai.photon import Photon

import fastchat.serve.controller


class Server(Photon):
    requirement_dependency = ["https://github.com/leptonai/FastChat.git@d426b61"]

    def init(self):
        controller = fastchat.serve.controller.Controller("shortest_queue")
        fastchat.serve.controller.controller = controller

    @Photon.handler(path="", mount=True)
    def subapp(self):
        return fastchat.serve.controller.app
