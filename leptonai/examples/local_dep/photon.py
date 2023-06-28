import os
from leptonai.photon import Photon


class MyPhoton(Photon):
    extra_files = {
        "./mydep-0.1-py3-none-any.whl": os.path.join(
            os.path.dirname(__file__), "mydep", "dist", "mydep-0.1-py3-none-any.whl"
        )
    }
    requirement_dependency = ["./mydep-0.1-py3-none-any.whl"]

    @Photon.handler()
    def run(self) -> bool:
        try:
            import mydep  # noqa: F401
        except ImportError:
            return False
        else:
            return True
