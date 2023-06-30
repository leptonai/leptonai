import os
import sys

from leptonai.photon import Photon


class FlaskPhoton(Photon):
    @Photon.handler("", mount=True)
    def flask_app(self):
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from app import app

        return app
