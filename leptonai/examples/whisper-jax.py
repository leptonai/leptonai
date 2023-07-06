"""This example demonstrates how to run optimized Whisper model on
Lepton.

[whisper-jax](https://github.com/sanchit-gandhi/whisper-jax.git) is a
JAX (optimized) port of the openai whisper model. It chunks audio data
into segments and then performs batch inference to gain speedup.

Installing JAX is a bit tricky, so here we provide a combination of
jax + jaxlib + cuda/cudnn pip versions that can work together inside
Lepton's default image.

"""

import os
from typing import Optional

from leptonai.photon import Photon


class Whisper(Photon):
    requirement_dependency = [
        "git+https://github.com/sanchit-gandhi/whisper-jax.git@0d3bc54",
        "nvidia-cudnn-cu11==8.6.0.163",
        "-f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html",
        "jax==0.4.13",
        "jaxlib==0.4.13+cuda11.cudnn86",
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

    @Photon.handler(
        "run",
        example={
            "inputs": (
                "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main/1.flac"
            )
        },
    )
    def run(self, inputs: str, task: Optional[str] = None):
        return self.pipeline(inputs, task=task)
