import sys
from leptonai.photon import Photon


class Counter(Photon):
    """
    A counter photon that uses a custom Docker image.
    """

    # Note that, the image should be accessible publicly. It can be a URL, or
    # an image in docker hub that you can normally `docker pull` with.
    # In this case, we are using the python slim images as an example.
    image = f"default/python:{sys.version_info.major}.{sys.version_info.minor}-slim"

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
