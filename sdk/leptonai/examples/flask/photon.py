from leptonai.photon import Photon


class FlaskPhoton(Photon):
    extra_files = {"flask_app-0.1-py3-none-any.whl": "flask_app-0.1-py3-none-any.whl"}
    requirement_dependency = ["flask_app-0.1-py3-none-any.whl"]

    @Photon.handler("", mount=True)
    def flask_app(self):
        from flask_app import app

        return app
