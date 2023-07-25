import gradio as gr
import torch

from leptonai.photon import Photon
from leptonai.photon.hf.hf_utils import create_diffusion_pipeline


class ImageGen(Photon):
    requirement_dependency = ["gradio", "torch"]

    def init(self):
        self.pipeline = create_diffusion_pipeline(
            "text-to-image", "runwayml/stable-diffusion-v1-5", "fp16"
        )

    def infer(self, prompt, samples, steps, scale, seed):
        if torch.cuda.is_available():
            device = torch.device("cuda")
        else:
            device = torch.device("cpu")
        generator = torch.Generator(device=device).manual_seed(seed)
        return self.pipeline(
            [prompt] * samples,
            num_inference_steps=steps,
            guidance_scale=scale,
            generator=generator,
        ).images

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
                ).style(grid=[2], height="auto")

                advanced_button = gr.Button("Advanced options", elem_id="advanced-btn")

            with gr.Row(elem_id="advanced-options"):
                samples = gr.Slider(
                    label="Images", minimum=1, maximum=4, value=1, step=1
                )
                steps = gr.Slider(
                    label="Steps", minimum=1, maximum=50, value=25, step=1
                )
                scale = gr.Slider(
                    label="Guidance Scale", minimum=0, maximum=50, value=7.5, step=0.1
                )
                seed = gr.Slider(
                    label="Seed",
                    minimum=0,
                    maximum=2147483647,
                    step=1,
                    randomize=True,
                )
            text.submit(
                self.infer, inputs=[text, samples, steps, scale, seed], outputs=gallery
            )
            btn.click(
                self.infer, inputs=[text, samples, steps, scale, seed], outputs=gallery
            )
            advanced_button.click(
                None,
                [],
                text,
            )

        return blocks
