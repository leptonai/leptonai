from leptonai.photon import Photon


class Foo(Photon):
    @Photon.handler
    def foo(self) -> str:
        return "hello world from Foo!"
