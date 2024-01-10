import os
import subprocess
import tempfile
from typing import Optional, Union
import uuid

from loguru import logger

from leptonai import ObjectStore
from leptonai.photon import Photon, Worker, File
from leptonai.util import is_valid_url


class StableVideoDiffusion(Worker):

    requirement_dependency = [
        "diffusers",
        "transformers",
        "accelerate",
        "opencv-python",
        "Pillow",
        "torch",
    ]

    deployment_template = {
        "resource_shape": "gpu.a10",
        "env": {
            # The model to use for the SVD task
            "SVD_MODEL": "stabilityai/stable-video-diffusion-img2vid-xt",
            # The bucket to use for input and output. It can be either a public
            # if you want your video files to be readily servable, or a private
            # bucket if you want to keep your video files private.
            "OBJECTSTORE_BUCKET": "public",
        },
    }

    OBJECTSTORE_INPUT_PREFIX = "stable-video-diffusion/input"
    OBJECTSTORE_OUTPUT_PREFIX = "stable-video-diffusion/output"

    def init(self):
        from diffusers import StableVideoDiffusionPipeline
        import torch

        model = os.environ["SVD_MODEL"]
        logger.info(f"Using model {model}")

        bucket = os.environ["OBJECTSTORE_BUCKET"]
        logger.info(f"Using bucket {bucket}")
        self._bucket = bucket

        objectstore_bucket = os.environ["OBJECTSTORE_BUCKET"]
        self._object_store = ObjectStore(objectstore_bucket)

        self.pipe = StableVideoDiffusionPipeline.from_pretrained(
            model,
            torch_dtype=torch.float16,
            variant="fp16",
        )
        self.pipe.enable_model_cpu_offload()
        super().init()

    # This is the main method you need to implement for the worker.
    def on_task(
        self,
        task_id: str,
        image: Union[str, dict],
        seed: Optional[int] = None,
        decode_chunk_size: int = 8,
        fps: int = 7,
        motion_bucket_id: int = 127,
        noise_aug_strength: float = 0.02,
    ):
        from diffusers.utils import load_image, export_to_video
        import torch

        if isinstance(image, tuple):
            bucket, key = image
            image = ObjectStore(bucket).get(key, return_url=True)
        image = load_image(image)
        image = image.resize((1024, 576))

        generator = torch.manual_seed(seed) if seed else None
        frames = self.pipe(
            image,
            decode_chunk_size=decode_chunk_size,
            generator=generator,
            motion_bucket_id=motion_bucket_id,
            noise_aug_strength=noise_aug_strength,
        ).frames[0]

        key = f"{self.OBJECTSTORE_OUTPUT_PREFIX}/{task_id}.mp4"
        with tempfile.NamedTemporaryFile(
            suffix=".mp4"
        ) as f_mpeg4, tempfile.NamedTemporaryFile(suffix=".mp4") as f_h264:
            export_to_video(frames, f_mpeg4.name, fps=fps)
            f_mpeg4.flush()
            # convert to h264
            subprocess.run([
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                f_mpeg4.name,
                "-vcodec",
                "h264",
                f_h264.name,
            ])
            f_h264.flush()
            f_h264.seek(0)
            logger.info(f"Uploading output to {self._bucket}/{key}")
            try:
                output_url = self._object_store.put(key, f_h264)
            except Exception as e:
                logger.error(f"Failed to upload output to {self._bucket}/{key}: {e}")
                raise
            else:
                logger.info(f"Uploaded output to {self._bucket}/{key}")

        if self._object_store.is_public:
            return {"url": output_url}
        else:
            return {"bucket": self._bucket, "key": key}

    @Photon.handler
    def run(
        self,
        image: Union[str, File],
        seed: Optional[int] = None,
        decode_chunk_size: int = 8,
        fps: int = 7,
        motion_bucket_id: int = 127,
        noise_aug_strength: float = 0.02,
    ):
        """
        Submits a SVD generation task to the worker. The task will be executed asynchronously.
        """
        if not is_valid_url(image):
            # When the image is not a valid url, upload the image to the object store.
            # so that the worker can download it.
            logger.info(f"image is not a url, uploading to {self._bucket}")

            # Load the conditioning image
            image = File(image)
            key = f"{self.OBJECTSTORE_INPUT_PREFIX}/{uuid.uuid4()}"
            try:
                output_url = self._object_store.put(key, image)
            except Exception as e:
                logger.error(f"Failed to upload input to {self._bucket}/{key}: {e}")
                raise
            else:
                logger.info(f"Uploaded input to {self._bucket}/{key}")

            if self._object_store.is_public:
                image = output_url
            else:
                image = {"bucket": self._bucket, "key": key}

        return self.task_post({
            "image": image,
            "seed": seed,
            "decode_chunk_size": decode_chunk_size,
            "fps": fps,
            "motion_bucket_id": motion_bucket_id,
            "noise_aug_strength": noise_aug_strength,
        })


if __name__ == "__main__":
    StableVideoDiffusion().launch()
