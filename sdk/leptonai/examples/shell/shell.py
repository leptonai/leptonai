import os

# This is what you should do to load the Photon class and write your code.
from leptonai.photon import Photon, handler


class Shell(Photon):
    def init(self):
        pass

    @handler("run")
    def run(self, query: str) -> str:
        """Run the shell. Don't do rm -rf though."""
        output = os.popen(query).read()
        return output
