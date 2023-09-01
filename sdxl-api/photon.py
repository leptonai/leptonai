import base64
from io import BytesIO
import os
import tempfile
from typing import Optional, List, Union

from diffusers import DiffusionPipeline, StableDiffusionXLInpaintPipeline
from diffusers.utils import load_image
from fastapi import FastAPI, Request
from loguru import logger
from prometheus_client import Counter as PrometheusCounter
import torch

from leptonai.photon import Photon, PNGResponse, HTTPException, FileParam


class SDXL(Photon):
    """Optimized SDXL pipeline running on [Lepton](https://lepton.ai)"""

    image: str = "605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:torch-flashattn2"

    requirement_dependency = [
        "torch",
        "diffusers>=0.19.3",
        "opencv-python!=4.8.0.76",
    ]

    def _optimize_pipeline(self, pipe):
        pipe.unet.to(memory_format=torch.channels_last)
        pipe.unet = torch.compile(pipe.unet, mode="reduce-overhead", fullgraph=True)
        return pipe

    def init(self):
        os.environ["PROMETHEUS_DISABLE_CREATED_SERIES"] = "1"
        self.steps_counter = PrometheusCounter(
            "steps",
            "steps counter",
            labelnames=["token"],
        )

        torch.backends.cuda.matmul.allow_tf32 = True

        # load both base & refiner
        self.base = DiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=torch.float16,
            variant="fp16",
            use_safetensors=True,
            add_watermarker=False,
        ).to("cuda")
        self._optimize_pipeline(self.base)

        self.refiner = DiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-refiner-1.0",
            text_encoder_2=self.base.text_encoder_2,
            vae=self.base.vae,
            torch_dtype=torch.float16,
            use_safetensors=True,
            variant="fp16",
            add_watermarker=False,
        ).to("cuda")
        self._optimize_pipeline(self.refiner)

        # TODO: can we share the txt2img and inpaint pipelines?
        kwargs = {
            key: getattr(self.base, key)
            for key in [
                "vae",
                "text_encoder",
                "text_encoder_2",
                "tokenizer",
                "tokenizer_2",
                "unet",
                "scheduler",
                "force_zeros_for_empty_prompt",
            ]
        }
        kwargs["add_watermarker"] = False
        self.inpaint_base = StableDiffusionXLInpaintPipeline(**kwargs).to("cuda")

        kwargs = {
            key: getattr(self.refiner, key)
            for key in [
                "vae",
                "text_encoder",
                "text_encoder_2",
                "tokenizer",
                "tokenizer_2",
                "unet",
                "scheduler",
                "requires_aesthetics_score",
                "force_zeros_for_empty_prompt",
            ]
        }
        kwargs["add_watermarker"] = False
        self.inpaint_refiner = StableDiffusionXLInpaintPipeline(**kwargs).to("cuda")

    def _user_error(self, detail):
        raise HTTPException(status_code=400, detail=detail)

    # There is a `run` function which is a copy of txt2img, remember
    # to update both if you change one.
    @Photon.handler(
        "txt2img",
        example={"prompt": "A cat launching rocket", "seed": 1234},
    )
    def txt2img(
        self,
        prompt: Optional[str] = None,
        prompt_2: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        negative_prompt_2: Optional[str] = None,
        prompt_embeds: List[List[List[float]]] = None,
        negative_prompt_embeds: List[List[List[float]]] = None,
        pooled_prompt_embeds: List[List[float]] = None,
        negative_pooled_prompt_embeds: List[List[float]] = None,
        width: int = 1024,
        height: int = 1024,
        guidance_scale: float = 5.0,
        seed: Optional[int] = None,
        steps: int = 30,
        high_noise_frac: float = 0.8,
        use_refiner: bool = False,
    ) -> PNGResponse:
        logger.info(
            f"Running txt2img with prompt='{prompt}', seed={seed}, steps={steps},"
            f" width={width}, height={height}, use_refiner={use_refiner}"
        )

        if prompt_embeds is not None:
            prompt_embeds = torch.tensor(
                prompt_embeds, dtype=torch.float16, device="cuda"
            )
        if pooled_prompt_embeds is not None:
            pooled_prompt_embeds = torch.tensor(
                pooled_prompt_embeds, dtype=torch.float16, device="cuda"
            )
        if negative_prompt_embeds is not None:
            negative_prompt_embeds = torch.tensor(
                negative_prompt_embeds, dtype=torch.float16, device="cuda"
            )
        if negative_pooled_prompt_embeds is not None:
            negative_pooled_prompt_embeds = torch.tenosr(
                negative_pooled_prompt_embeds, dtype=torch.float16, device="cuda"
            )
        if seed is not None:
            generator = torch.Generator(device="cuda").manual_seed(seed)
        else:
            generator = None

        base_extra_kwargs = {}
        if use_refiner:
            base_extra_kwargs["output_type"] = "latent"
            base_extra_kwargs["denoising_end"] = high_noise_frac
        images = self.base(
            prompt=prompt,
            prompt_2=prompt_2,
            negative_prompt=negative_prompt,
            negative_prompt_2=negative_prompt_2,
            prompt_embeds=prompt_embeds,
            pooled_prompt_embeds=pooled_prompt_embeds,
            negative_prompt_embeds=negative_prompt_embeds,
            negative_pooled_prompt_embeds=negative_pooled_prompt_embeds,
            width=width,
            height=height,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
            generator=generator,
            **base_extra_kwargs,
        ).images
        if use_refiner:
            images = self.refiner(
                prompt=prompt,
                prompt_2=prompt_2,
                negative_prompt=negative_prompt,
                negative_prompt_2=negative_prompt_2,
                prompt_embeds=prompt_embeds,
                pooled_prompt_embeds=pooled_prompt_embeds,
                negative_prompt_embeds=negative_prompt_embeds,
                negative_pooled_prompt_embeds=negative_pooled_prompt_embeds,
                num_inference_steps=steps,
                guidance_scale=guidance_scale,
                generator=generator,
                denoising_start=high_noise_frac,
                image=images,
            ).images

        img_io = BytesIO()
        images[0].save(img_io, format="PNG", quality="keep")
        img_io.seek(0)
        return PNGResponse(img_io, headers={"steps": str(steps)})

    # `run` is a copy of `txt2img`, we keep this just for backward compatibility
    @Photon.handler(
        "run",
        example={"prompt": "A cat launching rocket", "seed": 1234},
    )
    def run(
        self,
        prompt: Optional[str] = None,
        prompt_2: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        negative_prompt_2: Optional[str] = None,
        prompt_embeds: List[List[List[float]]] = None,
        negative_prompt_embeds: List[List[List[float]]] = None,
        pooled_prompt_embeds: List[List[float]] = None,
        negative_pooled_prompt_embeds: List[List[float]] = None,
        width: int = 1024,
        height: int = 1024,
        guidance_scale: float = 5.0,
        seed: Optional[int] = None,
        steps: int = 30,
        high_noise_frac: float = 0.8,
        use_refiner: bool = False,
    ) -> PNGResponse:
        return self.txt2img(
            prompt=prompt,
            prompt_2=prompt_2,
            negative_prompt=negative_prompt,
            negative_prompt_2=negative_prompt_2,
            prompt_embeds=prompt_embeds,
            negative_prompt_embeds=negative_prompt_embeds,
            pooled_prompt_embeds=pooled_prompt_embeds,
            negative_pooled_prompt_embeds=negative_pooled_prompt_embeds,
            width=width,
            height=height,
            guidance_scale=guidance_scale,
            seed=seed,
            steps=steps,
            high_noise_frac=high_noise_frac,
            use_refiner=use_refiner,
        )

    def _img_param_to_img(self, param):
        if isinstance(param, FileParam):
            file = tempfile.NamedTemporaryFile()
            file.write(param.file.read())
            file.flush()
            param = file.name
        elif isinstance(param, str):
            if not param.startswith("http://") and not param.startswith("https://"):
                # base64
                file = tempfile.NamedTemporaryFile()
                file.write(base64.b64decode(param.encode("ascii")))
                file.flush()
                param = file.name
        else:
            raise ValueError(f"Invalid image param: {param}")
        image = load_image(param).convert("RGB")
        return image

    @Photon.handler
    def inpaint(
        self,
        prompt: Optional[str] = None,
        prompt_2: Optional[str] = None,
        image: Union[str, FileParam] = None,
        mask_image: Union[str, FileParam] = None,
        negative_prompt: Optional[str] = None,
        negative_prompt_2: Optional[str] = None,
        prompt_embeds: List[List[List[float]]] = None,
        negative_prompt_embeds: List[List[List[float]]] = None,
        pooled_prompt_embeds: List[List[float]] = None,
        negative_pooled_prompt_embeds: List[List[float]] = None,
        width: int = 1024,
        height: int = 1024,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
        steps: int = 30,
        high_noise_frac: float = 0.8,
        use_refiner: bool = False,
    ) -> PNGResponse:
        logger.info(
            f"Running inpaint with prompt='{prompt}', seed={seed}, steps={steps},"
            f" width={width}, height={height}, use_refiner={use_refiner}"
        )

        if prompt_embeds is not None:
            prompt_embeds = torch.tensor(
                prompt_embeds, dtype=torch.float16, device="cuda"
            )
        if pooled_prompt_embeds is not None:
            pooled_prompt_embeds = torch.tensor(
                pooled_prompt_embeds, dtype=torch.float16, device="cuda"
            )
        if negative_prompt_embeds is not None:
            negative_prompt_embeds = torch.tensor(
                negative_prompt_embeds, dtype=torch.float16, device="cuda"
            )
        if negative_pooled_prompt_embeds is not None:
            negative_pooled_prompt_embeds = torch.tenosr(
                negative_pooled_prompt_embeds, dtype=torch.float16, device="cuda"
            )
        if seed is not None:
            generator = torch.Generator(device="cuda").manual_seed(seed)
        else:
            generator = None

        if image is not None:
            image = self._img_param_to_img(image)
        if mask_image is not None:
            mask_image = self._img_param_to_img(mask_image)

        base_extra_kwargs = {}
        if use_refiner:
            base_extra_kwargs["output_type"] = "latent"
            base_extra_kwargs["denoising_end"] = high_noise_frac
        images = self.inpaint_base(
            prompt=prompt,
            prompt_2=prompt_2,
            image=image,
            mask_image=mask_image,
            negative_prompt=negative_prompt,
            negative_prompt_2=negative_prompt_2,
            prompt_embeds=prompt_embeds,
            pooled_prompt_embeds=pooled_prompt_embeds,
            negative_prompt_embeds=negative_prompt_embeds,
            negative_pooled_prompt_embeds=negative_pooled_prompt_embeds,
            width=width,
            height=height,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
            generator=generator,
            **base_extra_kwargs,
        ).images
        if use_refiner:
            images = self.inpaint_refiner(
                prompt=prompt,
                prompt_2=prompt_2,
                negative_prompt=negative_prompt,
                negative_prompt_2=negative_prompt_2,
                prompt_embeds=prompt_embeds,
                pooled_prompt_embeds=pooled_prompt_embeds,
                negative_prompt_embeds=negative_prompt_embeds,
                negative_pooled_prompt_embeds=negative_pooled_prompt_embeds,
                num_inference_steps=steps,
                guidance_scale=guidance_scale,
                generator=generator,
                denoising_start=high_noise_frac,
                image=images,
                mask_image=mask_image,
            ).images

        img_io = BytesIO()
        images[0].save(img_io, format="PNG", quality="keep")
        img_io.seek(0)
        return PNGResponse(img_io, headers={"steps": str(steps)})

    @Photon.handler(mount=True)
    def do_not_look_at_it(self, app):
        fake_app = FastAPI()

        @app.middleware("http")
        async def update_steps_counter(request: Request, call_next):
            token = None
            auth_header = request.headers.get("Authorization")
            if auth_header is not None:
                auth_header = auth_header.strip()
                if auth_header.startswith("Bearer"):
                    token = auth_header.split("Bearer")[-1].strip()
                    logger.info(f"token={token}")

            response = await call_next(request)

            steps = None
            steps_str = response.headers.get("steps")
            if steps_str is not None:
                # remove the steps header so it doesn't get passed to
                # the client
                del response.headers["steps"]
                try:
                    steps = int(steps_str)
                except Exception:
                    pass
                else:
                    logger.info(f"steps={steps}")
            if token is not None and steps is not None:
                self.steps_counter.labels(token).inc(steps)

            return response

        return fake_app


if __name__ == "__main__":
    p = SDXL()
    p.launch()
