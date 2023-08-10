"""This example demonstrates how to run optimized Whisper model on
Lepton.

[whisper-jax](https://github.com/sanchit-gandhi/whisper-jax.git) is a
JAX (optimized) port of the openai whisper model. It chunks audio data
into segments and then performs batch inference to gain speedup.

Installing JAX is a bit tricky, so here we provide a combination of
jax + jaxlib + cuda/cudnn pip versions that can work together inside
Lepton's default image.

"""

from datetime import datetime, timedelta
import os
import tempfile
from typing import Optional, Dict, Any

from loguru import logger
import requests

from leptonai.photon import Photon, HTTPException


class Whisper(Photon):
    requirement_dependency = [
        "git+https://github.com/sanchit-gandhi/whisper-jax.git@0d3bc54",
        "cached_property",
        "nvidia-cudnn-cu11==8.6.0.163",
        "-f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html",
        "jax==0.4.13",
        "jaxlib==0.4.13+cuda11.cudnn86",
        "slack_sdk",
    ]

    system_dependency = [
        "ffmpeg",
    ]

    def init(self):
        from whisper_jax import FlaxWhisperPipline
        import jax.numpy as jnp

        model_id = os.environ.get("MODEL_ID", "openai/whisper-large-v2")
        batch_size = os.environ.get("BATCH_SIZE", 4)
        self.pipeline = FlaxWhisperPipline(
            model_id, dtype=jnp.float16, batch_size=batch_size
        )

        self._init_slack_bot()

    def _init_slack_bot(self):
        from slack_sdk import WebClient as SlackClient

        self._verification_token = os.environ.get("SLACK_VERIFICATION_TOKEN", None)
        self._slack_bot_token = os.environ.get("SLACK_BOT_TOKEN", None)
        if self._slack_bot_token:
            self._slack_bot_client = SlackClient(token=self._slack_bot_token)
        self._processed_slack_tasks = {}

    @Photon.handler(
        "run",
        example={
            "inputs": (
                "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/1.flac"
            )
        },
    )
    def run(self, inputs: str, task: Optional[str] = None):
        return self.pipeline(inputs, task=task)["text"]

    async def _slack_process_task(self, channel: str, thread_ts: str, url: str):
        last_processed_time = self._processed_slack_tasks.get((channel, url))
        if last_processed_time and datetime.now() - last_processed_time < timedelta(
            seconds=20
        ):
            logger.info(
                f"Skip processing slack task: ({channel}, {url}) since it was processed"
                f" recently: {last_processed_time}"
            )
            return

        logger.info(f"Processing audio file: {url}")
        with tempfile.NamedTemporaryFile("wb", suffix="." + url.split(".")[-1]) as f:
            logger.info(f"Start downloading audio file to: {f.name}")
            res = requests.get(
                url,
                allow_redirects=True,
                headers={"Authorization": f"Bearer {self._slack_bot_token}"},
            )
            res.raise_for_status()
            logger.info(f"Downloaded audio file (total bytes: {len(res.content)})")
            f.write(res.content)
            f.flush()
            f.seek(0)
            logger.info(f"Saved audio file to: {f.name}")
            logger.info(f"Running inference on audio file: {f.name}")
            try:
                text = self.run(f.name)
            except Exception as e:
                logger.error(f"Failed to run inference on audio file (f.name): {e}")
                return
            logger.info(f"Finished inference on audio file: {f.name}")
        self._slack_bot_client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=text,
        )
        if len(self._processed_slack_tasks) > 100:
            self._processed_slack_tasks = {
                k: v
                for k, v in self._processed_slack_tasks.items()
                if datetime.now() - v < timedelta(seconds=20)
            }
        self._processed_slack_tasks[(channel, url)] = datetime.now()

    @Photon.handler
    def slack(
        self,
        token: str,
        type: str,
        event: Optional[Dict[str, Any]] = None,
        challenge: Optional[str] = None,
        **extra,
    ) -> str:
        if not self._verification_token or not self._slack_bot_token:
            raise HTTPException(401, "Slack bot not configured")

        if token != self._verification_token:
            raise HTTPException(401, "Invalid token")

        if type == "url_verification":
            return challenge

        event_type = event["type"]
        logger.info(f"Received slack event: {event_type}")

        if event_type == "file_shared":
            channel = event["channel_id"]
            thread_ts = event.get("thread_ts")
            file_id = event["file_id"]
            file_info = self._slack_bot_client.files_info(file=file_id)
            if not file_info["ok"]:
                raise HTTPException(500, "Failed to get file info")
            self.add_background_task(
                self._slack_process_task,
                channel,
                thread_ts,
                file_info["file"]["url_private"],
            )
            return "ok"

        logger.info(f"Ignored slack event type: {event_type}")
