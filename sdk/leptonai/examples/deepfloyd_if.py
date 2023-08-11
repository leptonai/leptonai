from io import BytesIO
import os

from diffusers import DiffusionPipeline
from diffusers.pipelines.deepfloyd_if import fast27_timesteps, smart27_timesteps
from diffusers.utils import pt_to_pil
from loguru import logger
import gradio as gr
import torch

from leptonai.photon import Photon, PNGResponse


class If(Photon):
    requirement_dependency = [
        "diffusers==0.16.1",
        "torch==2.0.0",
        "torchvision==0.15.1",
        "gradio",
    ]

    def init(self):
        s1_model_size = os.environ.get("STAGE1_MODEL_SIZE", "M")
        if s1_model_size not in ["M", "L", "XL"]:
            raise ValueError(
                "STAGE1_MODEL_SIZE must be one of 'M', 'L', or 'XL', but got"
                f" {s1_model_size}"
            )
        s1_model = f"DeepFloyd/IF-I-{s1_model_size}-v1.0"
        logger.info(f"Using stage 1 model: {s1_model}")
        s2_model_size = os.environ.get("STAGE2_MODEL_SIZE", "M")
        if s2_model_size not in ["M", "L"]:
            raise ValueError(
                f"STAGE2_MODEL_SIZE must be one of 'M' or 'L', but got {s2_model_size}"
            )
        s2_model = f"DeepFloyd/IF-II-{s2_model_size}-v1.0"
        logger.info(f"Using stage 2 model: {s2_model}")

        enable_cpu_offload = os.environ.get("ENABLE_CPU_OFFLOAD", "1").lower() in [
            "true",
            "1",
        ]
        logger.info(f"Enable CPU offload: {enable_cpu_offload}")

        # stage 1
        self.stage_1 = DiffusionPipeline.from_pretrained(
            s1_model, variant="fp16", torch_dtype=torch.float16
        )
        if enable_cpu_offload:
            self.stage_1.enable_model_cpu_offload()
        else:
            self.stage_1.to("cuda")

        # stage 2
        self.stage_2 = DiffusionPipeline.from_pretrained(
            s2_model,
            text_encoder=None,
            variant="fp16",
            torch_dtype=torch.float16,
        )
        if enable_cpu_offload:
            self.stage_2.enable_model_cpu_offload()
        else:
            self.stage_2.to("cuda")
        # stage 3
        safety_modules = {
            "feature_extractor": self.stage_1.feature_extractor,
            "safety_checker": self.stage_1.safety_checker,
            "watermarker": self.stage_1.watermarker,
        }
        self.stage_3 = DiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-x4-upscaler",
            **safety_modules,
            torch_dtype=torch.float16,
        )
        if enable_cpu_offload:
            self.stage_3.enable_model_cpu_offload()
        else:
            self.stage_3.to("cuda")

    def _run(self, prompt: str, seed=0):
        res = []
        generator = torch.manual_seed(seed)

        # text embeds
        prompt_embeds, negative_embeds = self.stage_1.encode_prompt(prompt)
        # stage 1
        images = self.stage_1(
            prompt_embeds=prompt_embeds,
            negative_prompt_embeds=negative_embeds,
            generator=generator,
            output_type="pt",
            timesteps=fast27_timesteps,
        ).images
        res.append(pt_to_pil(images)[0])
        # stage 2
        images = self.stage_2(
            image=images,
            prompt_embeds=prompt_embeds,
            negative_prompt_embeds=negative_embeds,
            generator=generator,
            output_type="pt",
            timesteps=smart27_timesteps,
        ).images
        res.append(pt_to_pil(images)[0])
        # stage 3
        images = self.stage_3(
            prompt=prompt,
            image=images,
            generator=generator,
            noise_level=100,
            num_inference_steps=30,
        ).images
        res.append(images[0])

        return res

    @Photon.handler(
        example={
            "prompt": (
                "a photo of a kangaroo wearing an orange hoodie and blue sunglasses"
                ' standing in front of the eiffel tower holding a sign that says "very'
                ' deep learning"'
            )
        },
    )
    def run(self, prompt: str) -> PNGResponse:
        images = self._run(prompt=prompt)

        img_io = BytesIO()
        images[-1].save(img_io, format="PNG", quality="keep")
        img_io.seek(0)
        return PNGResponse(img_io)

    @Photon.handler(mount=True)
    def ui(self):
        blocks = gr.Blocks()

        with blocks:
            with gr.Group():
                with gr.Box():
                    with gr.Row().style(mobile_collapse=False, equal_height=True):
                        text = gr.Textbox(
                            label="Enter your prompt",
                            show_label=False,
                            max_lines=1,
                            placeholder="Enter your prompt",
                        ).style(
                            border=(True, False, True, True),
                            rounded=(True, False, False, True),
                            container=False,
                        )
                        btn = gr.Button("Generate image").style(
                            margin=False,
                            rounded=(False, True, True, False),
                        )
                gallery = gr.Gallery(
                    label="Generated images", show_label=False, elem_id="gallery"
                ).style(grid=[3], height="auto")

            with gr.Row(elem_id="advanced-options"):
                seed = gr.Slider(
                    label="Seed",
                    minimum=0,
                    maximum=2147483647,
                    step=1,
                    randomize=True,
                )
            btn.click(self._run, inputs=[text, seed], outputs=gallery)
        return blocks
