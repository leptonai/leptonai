from ..photon import Photon
from .vllm import vLLM  # noqa: F401


class Echo(Photon):
    @Photon.handler
    def run(self, input: str) -> str:
        return input
