import os
import sys
import time
from typing import List, Optional, Union

from threading import Lock
import numpy as np

from leptonai.photon import Photon, HTTPException
from leptonai.photon.types import File

from loguru import logger


class WhisperX(Photon):
    """
    A WhisperX photon that serves the [WhisperX](https://github.com/m-bain/whisperX) model.

    The photon exposes a single endpoint "/run" that takes an audio file as input, and returns
    the transcription, and alignment, and diarization results.
    """

    # Note: openai-whisper implicitly requires triton 2.1.0, which in turn might be in conflict
    # with non-version-pinned torch and torchaudio. As a result, we will pin all three versions
    # here.
    requirement_dependency = [
        "numpy",
        "torchaudio",
        "pyannote.audio==3.1.1",
        "git+https://github.com/m-bain/whisperx.git@e9c507ce5dea0f93318746411c03fed0926b70be",
    ]

    system_dependencies = ["ffmpeg"]

    deployment_template = {
        "resource_shape": "gpu.a10",
        "env": {
            "WHISPER_MODEL": "large-v3",
            # maximum audio length that the api allows. In default, we will use
            # 10 minutes. If you are deploying things on your own, you can change
            # it to be longer.
            "MAX_LENGTH_IN_SECONDS": "600",
        },
        "secret": [
            "HUGGING_FACE_HUB_TOKEN",
        ],
    }

    # If one is doing a lot of alignments and diarizations, it is possible that
    # the gpu is underutilized. In this case, one can increase the concurrency
    # to better utilize the gpu.
    handler_max_concurrency = 8

    SUPPORTED_LANGUAGES = {"en", "fr", "de", "es", "it", "ja", "zh", "nl", "uk", "pt"}
    # The main language for the model
    MAIN_LANGUAGE = "en"
    # batch size that is benchmarked to be the best balance on A10
    DEFAULT_BATCH_SIZE = 16

    # Because each alignment language takes a nontrivial amount of memory,
    # we only keep languages that we find are commonly called, and load other
    # models on-demand. You can change this to host more alignment models in a
    # warm state at the cost of more memory.
    ALIGNMENT_LANGUAGE_TO_KEEP = {"en", "zh", "es"}

    def init(self):
        import torch
        import whisperx
        from whisperx.asr import FasterWhisperPipeline

        logger.info("Initializing WhisperX")

        self.USE_FASTER_WHISPER = True
        self.WHISPER_MODEL = os.environ["WHISPER_MODEL"]
        self.MAX_LENGTH_IN_SECONDS = int(os.environ["MAX_LENGTH_IN_SECONDS"])

        # 1. Load whisper model
        self.hf_token = os.environ["HUGGING_FACE_HUB_TOKEN"]
        if not self.hf_token:
            logger.error("Please set the environment variable HUGGING_FACE_HUB_TOKEN.")
            sys.exit(1)
        if torch.cuda.is_available():
            self.device = "cuda"
            compute_type = "float16"
        else:
            self.device = "cpu"
            compute_type = "float32"

        # 1. load whisper model
        # We keep a main model as MAIN_LANGUAGE so we don't need to always reload
        # tokenizers. We also keep a multilingual model that can handle all languages.
        self._main_model = whisperx.load_model(
            self.WHISPER_MODEL,
            self.device,
            compute_type=compute_type,
            language=self.MAIN_LANGUAGE,
        )
        self._multilingual_model = FasterWhisperPipeline(
            model=self._main_model.model,
            vad=self._main_model.vad_model,
            options=self._main_model.options,
            tokenizer=None,
            language=None,
            suppress_numerals=self._main_model.suppress_numerals,
            vad_params=self._main_model._vad_params,
        )
        # For the main model, inference is not thread safe (because of some underlying cuda memory
        # accesses). As a result, whenever we use the transcribe model, we need to lock it.
        self.transcribe_model_lock = Lock()

        # 2. load whisper align model. Alignment models are language specific, so we will basically
        # load them as a dictionary. In addition, we only load models that are in ALIGNMENT_LANGUAGE_TO_KEEP.
        self._model_a = {}
        self._metadata = {}
        for lang in self.ALIGNMENT_LANGUAGE_TO_KEEP:
            self._model_a[lang], self._metadata[lang] = whisperx.load_align_model(
                language_code=lang, device=self.device
            )
        # Since we don't know if whisper's align function is perfectly thread safe or not, we
        # will lock it as well.
        self.align_model_lock = Lock()

        # 3. load whisper diarize model. Diarization model right now is thread safe.
        self._diarize_model = whisperx.DiarizationPipeline(
            model_name="pyannote/speaker-diarization@2.1",
            use_auth_token=self.hf_token,
            device=self.device,
        )
        self._diarize_model_lock = Lock()

    def _transcribe(
        self, audio: np.ndarray, audio_file, language: Optional[str] = None
    ):
        logger.debug("transcribe: aquiring lock")
        with self.transcribe_model_lock:
            logger.debug("transcribe: lock acquired")
            if language == self.MAIN_LANGUAGE:
                result = self._main_model.transcribe(
                    audio, batch_size=self.DEFAULT_BATCH_SIZE, language=language
                )
            else:
                result = self._multilingual_model.transcribe(
                    audio, batch_size=self.DEFAULT_BATCH_SIZE, language=language
                )
        logger.debug("transcribe: lock released")
        return result

    def _align(self, result, audio):
        # Run alignment
        import whisperx

        logger.debug("Start alignment")
        if result["language"] in self.SUPPORTED_LANGUAGES:
            model_a = self._model_a[result["language"]]
            metadata_a = self._metadata[result["language"]]
        else:
            # load model_a and metadata on-demand
            model_a, metadata_a = whisperx.load_align_model(
                language_code=result["language"], device=self.device
            )
        with self.align_model_lock:
            result = whisperx.align(
                result["segments"],
                model_a,
                metadata_a,
                audio,
                self.device,
                return_char_alignments=False,
            )
        logger.debug("alignment done.")
        return result

    def _diarize(self, audio, min_speakers, max_speakers):
        logger.debug("Start diarization")
        with self._diarize_model_lock:
            result = self._diarize_model(
                audio,
                min_speakers=min_speakers,
                max_speakers=max_speakers,
            )
        logger.debug("diarization done.")
        return result

    @Photon.handler(
        example={
            "input": (
                "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/1.flac"
            ),
            "language": "en",
            "transcribe_only": True,
        },
        cancel_on_disconnect=1.0,
    )
    def run(
        self,
        input: Union[str, File],
        language: Optional[str] = "en",
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
        transcribe_only: bool = True,
    ) -> List:
        """
        Runs transcription, alignment, and diarization for the input.

        - Inputs:
            - input: a string that is an url containing the audio file, or a base64-encoded
            string containing an audio file content.
            - language(optional): the language code for the input. If not provided, the model
                will try to detect the language automatically (note this runs more slowly)
            - min_speakers(optional): the hint for minimum number of speakers for diarization.
            - max_speakers(optional): the hint for maximum number of speakers for diarization.
            - transcribe_only(optional): if True, only transcribe the audio, and skip alignment
                and diarization. Default to True.

        - Returns:
            - result: The transcribe and/or aligned and diarized result. If transcribe_only,
                the result contains only the transcription
        """
        import whisperx

        # Check input
        if language is not None and language not in self.SUPPORTED_LANGUAGES:
            raise HTTPException(
                400,
                f"Unsupported language: {language}. Supported languages:"
                f" {self.SUPPORTED_LANGUAGES}",
            )
        if min_speakers is not None and min_speakers < 1:
            raise HTTPException(400, f"min_speakers must be >= 1, got {min_speakers}")
        if max_speakers is not None and max_speakers < 1:
            raise HTTPException(400, f"max_speakers must be >= 1, got {max_speakers}")
        if (
            min_speakers is not None
            and max_speakers is not None
            and min_speakers > max_speakers
        ):
            raise HTTPException(
                400,
                f"min_speakers must be <= max_speakers, got {min_speakers} >"
                f" {max_speakers}",
            )

        start_time = time.time()
        logger.debug(f"Start processing audio {input}")
        if isinstance(input, str):
            input = File(input)
        audio_file = input.get_temp_file()
        audio = whisperx.load_audio(audio_file.name)
        if audio.size > self.MAX_LENGTH_IN_SECONDS * 16000:
            raise HTTPException(
                400,
                f"Audio length {audio.size / 16000} seconds is longer than the maximum"
                f" allowed length {self.MAX_LENGTH_IN_SECONDS} seconds.",
            )
        logger.debug(f"started processing audio of length {len(audio)}.")
        # Note: audio_file is basically provided so we can run whisper if needed. Whisper
        # uses a different loading mechanism, and as a result it is slightly different from
        # the whisperx loaded audio.
        result = self._transcribe(audio, audio_file, language=language)
        logger.debug("Transcription done.")

        if len(result["segments"]) == 0:
            logger.debug("Empty result from whisperx. Directly return empty.")
            return []

        if transcribe_only:
            total_time = time.time() - start_time
            logger.debug(
                f"finished processing audio of len {audio.size}. Total"
                f" time: {total_time} ({audio.size / 16000 / total_time} x realtime)"
            )
            return result["segments"]

        # Run alignment and diarization
        result = self._align(result, audio)

        # When there is no active diarization, the diarize model throws a KeyError.
        # In this case, we simply skip diarization.
        try:
            diarize_segments = self._diarize(audio, min_speakers, max_speakers)
        except Exception as e:
            logger.error(f"Error in diarization: {e}. Skipping diarization.")
        else:
            result = whisperx.assign_word_speakers(diarize_segments, result)

        total_time = time.time() - start_time
        logger.debug(
            f"finished processing audio of len {audio.size}. Total"
            f" time: {total_time} ({audio.size / 16000 / total_time} x realtime)"
        )
        return result["segments"]

    @Photon.handler(method="GET")
    def model(self) -> str:
        """
        Returns the whisper model string.
        """
        return self.WHISPER_MODEL


if __name__ == "__main__":
    p = WhisperX()
    p.launch()
