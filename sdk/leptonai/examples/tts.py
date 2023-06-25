import base64
from io import BytesIO
from typing import List, Optional

import gradio as gr
from loguru import logger
import torch
from TTS.api import TTS

from leptonai.photon import Photon, WAVResponse


class Speaker(Photon):
    requirement_dependency = ["TTS"]

    def init(self):
        pass

    def _load_model(self, name):
        logger.info(f"Loading model {name}")
        if torch.cuda.is_available():
            logger.info("Using GPU")
            kwargs = {"gpu": True}
        else:
            logger.info("Using CPU")
            kwargs = {"gpu": False}
        self._model_name = name
        self._model = TTS(name, **kwargs)
        logger.info(f"Loaded model {name}")

        logger.info(f"Model has languages {self.languages}")
        logger.info(f"Model has speakers {self.speakers}")

        return (
            gr.Dropdown.update(
                choices=self.languages,
                visible=bool(self.languages),
                value=self.languages[0] if self.languages else None,
            ),
            gr.Dropdown.update(
                choices=self.speakers,
                visible=bool(self.speakers),
                value=self.speakers[0] if self.speakers else None,
            ),
        )

    @property
    def model_name(self):
        if not hasattr(self, "_model_name"):
            return None
        return self._model_name

    @property
    def languages(self):
        return self._model.languages or []

    @property
    def speakers(self):
        return self._model.speakers or []

    @Photon.handler()
    def list_models(self) -> List[str]:
        return TTS.list_models()

    def _tts(
        self, text: str, language: Optional[str] = None, speaker: Optional[str] = None
    ) -> BytesIO:
        logger.info(
            f"Synthesizing '{text}' with language '{language}' and speaker '{speaker}'"
        )
        if not language:
            if self.languages:
                language = self.languages[0]
            else:
                language = None
        if not speaker:
            if self.speakers:
                speaker = self.speakers[0]
            else:
                speaker = None
        wav = self._model.tts(
            text=text,
            language=language,
            speaker=speaker,
        )
        wav_io = BytesIO()
        self._model.synthesizer.save_wav(wav, wav_io)
        wav_io.seek(0)
        return wav_io

    @Photon.handler()
    def tts(
        self, text: str, language: Optional[str] = None, speaker: Optional[str] = None
    ) -> WAVResponse:
        wav_io = self._tts(text=text, language=language, speaker=speaker)
        return WAVResponse(wav_io)

    @Photon.handler(mount=True)
    def ui(self):
        blocks = gr.Blocks()

        with blocks:
            with gr.Column():
                model = gr.Dropdown(choices=self.list_models(), label="Model")
                language = gr.Dropdown(label="Language", visible=False)
                speaker = gr.Dropdown(label="Speaker", visible=False)
                model.change(
                    self._load_model, inputs=[model], outputs=[language, speaker]
                )

                text = gr.Textbox(label="Text", max_lines=3)

            with gr.Column():
                audio = gr.HTML(label="Audio")

            text.submit(
                fn=lambda *args, **kwargs: f"""<audio src="data:audio/mpeg;base64,{base64.b64encode(self._tts(*args, **kwargs).read()).decode('utf-8')}" controls autoplay></audio>""",
                inputs=[text, language, speaker],
                outputs=[audio],
            )

        return blocks
