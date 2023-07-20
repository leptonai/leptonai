import base64
from io import BytesIO
import os
from typing import List, Union
import uuid

from audiocraft.models import MusicGen
from audiocraft.data.audio import audio_write
import gradio as gr
from leptonai.photon import Photon, WAVResponse
from loguru import logger


class Server(Photon):
    requirement_dependency = ["audiocraft"]

    def init(self):
        self.model = MusicGen.get_pretrained(os.environ.get("MODEL", "small"))
        self.model.set_generation_params(duration=os.environ.get("DURATION", 8))

    @Photon.handler(max_batch_size=4, max_wait_time=1)
    def run(self, description: str) -> WAVResponse:
        wav_ios = self._run(description)
        return [WAVResponse(wav_io) for wav_io in wav_ios]

    def _run(
        self, descriptions: Union[str, List[str]]
    ) -> Union[BytesIO, List[BytesIO]]:
        logger.info(f"Generating audio for descriptions={descriptions}")
        is_batched = isinstance(descriptions, list)
        if not is_batched:
            descriptions = [descriptions]
        wavs = self.model.generate(descriptions)

        buffers = []
        for idx, wav in enumerate(wavs):
            fn = uuid.uuid4().hex
            audio_write(fn, wav.cpu(), self.model.sample_rate, strategy="loudness")
            # so weird
            fn = f"{fn}.wav"
            with open(fn, "rb") as f:
                buf = BytesIO(f.read())
                buf.flush()
                buf.seek(0)
            os.remove(fn)
            buffers.append(buf)
        if not is_batched:
            buffers = buffers[0]
        return buffers

    @Photon.handler(mount=True)
    def ui(self):
        blocks = gr.Blocks()

        with blocks:
            with gr.Column():
                text = gr.Textbox(label="Text", max_lines=3)

            with gr.Column():
                audio = gr.HTML(label="Audio")

            text.submit(
                fn=lambda text: f"""<audio src="data:audio/mpeg;base64,{base64.b64encode(self._run(text).read()).decode('utf-8')}" controls autoplay></audio>""",
                inputs=[text],
                outputs=[audio],
            )

        return blocks
