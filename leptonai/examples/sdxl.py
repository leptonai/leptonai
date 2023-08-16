from io import BytesIO
from typing import Optional

from diffusers import DiffusionPipeline
import gradio as gr
import torch

from leptonai.photon import Photon, PNGResponse


class ImageGen(Photon):
    requirement_dependency = ["gradio", "torch", "diffusers>=0.19.0"]

    def init(self):
        cuda_available = torch.cuda.is_available()

        if cuda_available:
            self.device = torch.device("cuda")
        else:
            self.device = torch.device("cpu")

        # load both base & refiner
        self.base = DiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=torch.float16,
            variant="fp16",
            use_safetensors=True,
        )
        if cuda_available:
            self.base.to("cuda")
            # TODO: enable torch.compile once thie issue is fixed:
            # https://github.com/huggingface/diffusers/issues/4375
            # self.base.unet = torch.compile(self.base.unet, mode="reduce-overhead", fullgraph=True)

        self._refiner = None

    @property
    def refiner(self):
        if self._refiner is None:
            pipe = DiffusionPipeline.from_pretrained(
                "stabilityai/stable-diffusion-xl-refiner-1.0",
                text_encoder_2=self.base.text_encoder_2,
                vae=self.base.vae,
                torch_dtype=torch.float16,
                use_safetensors=True,
                variant="fp16",
            )
            if torch.cuda.is_available():
                pipe.to("cuda")
                # TODO: enable torch.compile once thie issue is fixed:
                # https://github.com/huggingface/diffusers/issues/4375
                # pipe.unet = torch.compile(pipe.unet, mode="reduce-overhead", fullgraph=True)
            self._refiner = pipe
        return self._refiner

    @Photon.handler(
        "run",
        example={
            "prompt": "A majestic lion jumping from a big stone at night",
            "n_steps": 40,
            "high_noise_frac": 0.8,
        },
    )
    def run(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        guidance_scale: Optional[float] = 5.0,
        seed: Optional[int] = None,
        num_inference_steps: Optional[int] = 50,
        high_noise_frac: Optional[float] = 0.8,
        use_refiner: Optional[bool] = True,
    ) -> PNGResponse:
        images = self._run(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            guidance_scale=guidance_scale,
            samples=1,
            seed=seed,
            num_inference_steps=num_inference_steps,
            high_noise_frac=high_noise_frac,
            use_refiner=use_refiner,
        )

        img_io = BytesIO()
        images[0].save(img_io, format="PNG", quality="keep")
        img_io.seek(0)
        return PNGResponse(img_io)

    def _run(
        self,
        prompt,
        negative_prompt,
        width,
        height,
        guidance_scale,
        samples,
        seed,
        num_inference_steps,
        high_noise_frac,
        use_refiner,
    ):
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        else:
            generator = None

        if samples > 1:
            prompt = [prompt] * samples
            if negative_prompt is not None:
                negative_prompt = [negative_prompt] * samples
            generator = [generator] * samples

        base_extra_kwargs = {}
        if use_refiner:
            base_extra_kwargs["output_type"] = "latent"
            base_extra_kwargs["denoising_end"] = high_noise_frac
        # run both experts
        images = self.base(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            guidance_scale=guidance_scale,
            generator=generator,
            num_inference_steps=num_inference_steps,
            **base_extra_kwargs,
        ).images
        if use_refiner:
            images = self.refiner(
                prompt=prompt,
                negative_prompt=negative_prompt,
                guidance_scale=guidance_scale,
                num_inference_steps=num_inference_steps,
                generator=generator,
                denoising_start=high_noise_frac,
                image=images,
            ).images
        return images

    @Photon.handler(mount=True)
    def ui(self):
        blocks = gr.Blocks()

        with blocks:
            with gr.Group():
                with gr.Box():
                    with gr.Column(scale=3):
                        with gr.Row():
                            prompt = gr.Textbox(
                                label="Enter your prompt",
                                show_label=False,
                                max_lines=1,
                                placeholder="Enter your prompt",
                            ).style(
                                border=(True, False, True, True),
                                rounded=(True, False, False, True),
                                container=False,
                            )
                        with gr.Row():
                            negative_prompt = gr.Textbox(
                                label="Enter your prompt",
                                show_label=False,
                                max_lines=1,
                                placeholder="Enter your prompt",
                            ).style(
                                border=(True, False, True, True),
                                rounded=(True, False, False, True),
                                container=False,
                            )
                    with gr.Column(scale=1):
                        btn = gr.Button("Generate image").style(
                            margin=False,
                            rounded=(False, True, True, False),
                        )
                gallery = gr.Gallery(
                    label="Generated images", show_label=False, elem_id="gallery"
                ).style(grid=[2], height="auto")

            with gr.Row(elem_id="advanced-options-1"):
                samples = gr.Slider(
                    label="Images", minimum=1, maximum=4, value=1, step=1
                )
                width = gr.Slider(
                    label="Width",
                    minimum=64,
                    maximum=1024,
                    value=512,
                    step=8,
                )
                height = gr.Slider(
                    label="Height",
                    minimum=64,
                    maximum=1024,
                    value=512,
                    step=8,
                )
                steps = gr.Slider(
                    label="Steps", minimum=1, maximum=50, value=25, step=1
                )
            with gr.Row(elem_id="advanced-options-2"):
                scale = gr.Slider(
                    label="Guidance Scale", minimum=0, maximum=50, value=7.5, step=0.1
                )
                high_noise_frac = gr.Slider(
                    label="Denoising fraction",
                    minimum=0,
                    maximum=1,
                    value=0.8,
                    step=0.1,
                )
                seed = gr.Slider(
                    label="Seed",
                    minimum=0,
                    maximum=2147483647,
                    value=142857,
                    step=1,
                )
                use_refiner = gr.Checkbox(label="Use refiner", value=True)
            btn.click(
                self._run,
                inputs=[
                    prompt,
                    negative_prompt,
                    width,
                    height,
                    scale,
                    samples,
                    seed,
                    steps,
                    high_noise_frac,
                    use_refiner,
                ],
                outputs=gallery,
            )

        return blocks
