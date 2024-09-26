import os
import tempfile
from leptonai.photon import Photon
from typing import Union, Iterable
from fastapi import UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse


class Transcriber(Photon):
    # The init method implements any custom initialization logic we need.
    requirement_dependency = [
        "Cython",
        "packaging",
        "nemo_toolkit[asr]",
        "huggingface-hub==0.23.2",
        "numpy==1.26.3",
    ]
    system_dependency = ["libsndfile1", "ffmpeg"]

    deployment_template = {
        "resource_shape": "gpu.a10",
        "env": {"NEMO_MODEL": "nvidia/canary-1b"},
    }

    def init(self):
        from nemo.collections.asr.models import ASRModel

        self.NEMO_MODEL = os.environ["NEMO_MODEL"]
        self.asr_model = ASRModel.from_pretrained(self.NEMO_MODEL)

    # When no name is specified, the handler name is the method name.
    @Photon.handler("/transcribe_audio/", method="POST", use_raw_args=True)
    async def transcribe_audio(
        self,
        file: UploadFile,
        batch_size: int = Form(4),
        logprobs: bool = Form(None),
        return_hypotheses: bool = Form(False),
        num_workers: int = Form(0),
        channel_selector: Union[int, Iterable[int], str, None] = Form(None),
        verbose: bool = Form(True),
    ) -> JSONResponse:
        """
        Transcribes the audio file sent in a .wav format.
        """
        try:

            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
                tmp.write(await file.read())
                tmp.flush()  # Ensure all data is written
                tmp_path = tmp.name

                # Use the temporary file path for transcription
                transcript = self.asr_model.transcribe(
                    paths2audio_files=[tmp_path],  # Pass the temporary file path
                    batch_size=batch_size,
                    logprobs=logprobs,
                    return_hypotheses=return_hypotheses,
                    num_workers=num_workers,
                    channel_selector=channel_selector,
                    verbose=verbose,
                )

            # Return the transcript as a JSONResponse
            return JSONResponse(content=transcript)

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @Photon.handler(method="GET")
    def model(self) -> JSONResponse:
        """
        Returns the Nemo model string.
        """
        return JSONResponse(content=self.NEMO_MODEL)
