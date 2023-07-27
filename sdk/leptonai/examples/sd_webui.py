import os
import sys

from loguru import logger

from leptonai.photon import Photon


class WebUI(Photon):
    vcs_url: str = "https://github.com/AUTOMATIC1111/stable-diffusion-webui.git@v1.5.0"
    requirement_dependency = ["loguru", "gradio==3.32.0", "pydantic<2.0.0"]
    system_dependency = ["libgl1"]

    @Photon.handler("", mount=True)
    def ui(self, app):
        # current directory should be a checkout of stable-diffusion-webui
        # git repo, adding it to sys.path so that we can `import modules`
        sys.path.append(os.getcwd())

        # force webui to do parse_known_args() instead of parse_args()
        os.environ["IGNORE_CMD_ARGS_ERRORS"] = "1"

        from modules import launch_utils

        logger.info("preparing webui environment")
        launch_utils.prepare_environment()

        import webui

        logger.info("initializing webui")
        webui.initialize()
        logger.info("done")

        from modules import script_callbacks

        script_callbacks.before_ui_callback()

        from modules import ui

        blocks = ui.create_ui()

        from modules import shared

        shared.demo = blocks

        from modules import progress

        progress.setup_progress_api(app)
        ui.setup_ui_api(app)
        webui.create_api(app)

        from modules import ui_extra_networks

        ui_extra_networks.add_pages_to_demo(app)

        script_callbacks.app_started_callback(blocks, app)

        return blocks
