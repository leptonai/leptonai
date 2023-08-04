import asyncio
import time

from leptonai.photon import Photon
from loguru import logger


class Server(Photon):
    async def async_run_in_background(self, task):
        logger.info(f"Running async task '{task}'")
        # sleep here to simulate a long running task
        await asyncio.sleep(2)
        logger.info(f"Async task '{task}' completed")

    def run_in_background(self, task):
        logger.info(f"Running task '{task}'")
        # sleep here to simulate a long running task
        time.sleep(2)
        logger.info(f"Task '{task}' completed")

    @Photon.handler
    def run(self, task: str):
        self.add_background_task(self.run_in_background, task)
        self.add_background_task(self.async_run_in_background, f"async {task}")
        return {"status": "ok"}
