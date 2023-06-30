import os

try:
    # the old way, when we have the Runner class. You should not use this
    # any more. Use the new Photon class.
    from leptonai.photon.runner import RunnerPhoton as Runner, handler

    Photon = Runner
except ImportError:
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
