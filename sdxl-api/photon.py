from io import BytesIO
import os
from typing import Optional, List

from diffusers import DiffusionPipeline
from fastapi import FastAPI, Request
from loguru import logger
from prometheus_client import Counter as PrometheusCounter
import torch

from leptonai.photon import Photon, PNGResponse, HTTPException


class SDXL(Photon):
    image: str = "605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:torch-flashattn2"

    requirement_dependency = [
        "torch",
        "diffusers>=0.19.3",
    ]

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
        self.base.unet.to(memory_format=torch.channels_last)
        self.base.unet = torch.compile(
            self.base.unet, mode="reduce-overhead", fullgraph=True
        )

        self.refiner = DiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-refiner-1.0",
            text_encoder_2=self.base.text_encoder_2,
            vae=self.base.vae,
            torch_dtype=torch.float16,
            use_safetensors=True,
            variant="fp16",
            add_watermarker=False,
        ).to("cuda")
        self.refiner.unet.to(memory_format=torch.channels_last)
        self.refiner.unet = torch.compile(
            self.refiner.unet, mode="reduce-overhead", fullgraph=True
        )

    def _user_error(self, detail):
        raise HTTPException(status_code=400, detail=detail)

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

    @Photon.handler(mount=True)
    def do_not_look_at_it(self, app):
        fake_app = FastAPI()

        @app.middleware("http")
        async def update_steps_counter(request: Request, call_next):
            token = None
            auth_header = request.headers.get("Authorization")
            logger.info(f"auth_header={auth_header}")
            if auth_header is not None:
                auth_header = auth_header.strip()
                if auth_header.startswith("Bearer"):
                    token = auth_header.split("Bearer")[-1].strip()
            logger.info(f"token={token}")

            response = await call_next(request)

            steps = None
            steps_str = response.headers.get("steps")
            logger.info(f"steps_str={steps_str}")
            if steps_str is not None:
                try:
                    steps = int(steps_str)
                except Exception:
                    pass
            logger.info(f"steps={steps}")
            if token is not None and steps is not None:
                self.steps_counter.labels(token).inc(steps)

            return response

        return fake_app


if __name__ == "__main__":
    p = SDXL()
    p.launch()
