# This is a simple example to show how one can use the pickled utility. Note again
# that pickle comes with a lot of side effects, and should be used in caution.

from leptonai.photon import Photon, handler
from leptonai.photon.types import lepton_pickle, LeptonPickled


class Pickle(Photon):
    def init(self):
        pass

    @handler("run")
    def run(self) -> LeptonPickled:
        output = [
            "Hello, world!",
            {"key": "value"},
            {"key": [1, 2, 3]},
            (1, 2, 3),
            (1, "2", 3.0, {"four": 4}),
        ]
        return lepton_pickle(output)
