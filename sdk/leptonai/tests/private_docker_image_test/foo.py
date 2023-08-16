from leptonai.photon import Photon


class Foo(Photon):
    image = "leptonai/base:latest"

    def init(self):
        pass

    @Photon.handler
    def foo(self):
        return
