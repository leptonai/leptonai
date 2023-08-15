"""
Photon for launching JupyterLab.
"""

import os

from leptonai.photon import Photon
from leptonai.config import DEFAULT_PORT


class Notebook(Photon):
    requirement_dependency = ["jupyterlab"]

    def launch(self, host="0.0.0.0", port=DEFAULT_PORT, log_level="info"):
        return os.execvp(
            "jupyter",
            [
                "jupyter",
                "lab",
                "--no-browser",
                "--allow-root",
                "--ip",
                host,
                "--port",
                str(port),
                "--NotebookApp.allow_origin",
                "*",
                "--NotebookApp.token",
                "",
                "--NotebookApp.password",
                "",
            ],
        )
