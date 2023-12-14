import subprocess
from typing import Tuple

# This is what you should do to load the Photon class and write your code.
from leptonai.photon import Photon, handler


class Shell(Photon):
    def init(self):
        pass

    @handler("run", example={"query": "pwd"})
    def run(self, query: str) -> Tuple[str, str]:
        """Run the shell. Don't do rm -rf though."""
        output = subprocess.run(
            query, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        stdout_output = output.stdout.strip()
        stderr_output = output.stderr.strip()

        return stdout_output, stderr_output
