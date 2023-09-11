from ..photon import Photon


class Echo(Photon):
    @Photon.handler
    def run(self, input: str) -> str:
        return input
