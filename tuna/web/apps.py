import os

from dotenv import load_dotenv
from django.apps import AppConfig
from loguru import logger
from logtail import LogtailHandler


class WebConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "web"

    def ready(self):
        if not os.environ.get("LOGTAIL_TOKEN") and os.path.exists(".env.logtail"):
            load_dotenv(".env.logtail")

        if os.environ.get("LOGTAIL_TOKEN"):
            logtail_handler = LogtailHandler(source_token=os.environ["LOGTAIL_TOKEN"])
            logger.add(logtail_handler, level="DEBUG", format="{message}")
