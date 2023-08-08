import sys
from leptonai.photon import Photon


class Counter(Photon):
    image = f"python:{sys.version_info.major}.{sys.version_info.minor}-slim"

    def init(self):
        self.counter = 0

    @Photon.handler("add")
    def add(self, x: int) -> int:
        self.counter += x
        return self.counter

    @Photon.handler("sub")
    def sub(self, x: int) -> int:
        self.counter -= x
        return self.counter
