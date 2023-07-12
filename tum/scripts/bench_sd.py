import argparse
import logging

import torch
from leptonai.photon.hf_utils import create_diffusion_pipeline

# mute diffusers logging
logging.getLogger("diffusers.pipelines.pipeline_utils").setLevel(logging.ERROR)


def benchmark(func, num_warmup, num_runs):
    print("Start warmup")
    for i in range(num_warmup):
        _ = func()
    print("Warmup finished")

    res = []
    for i in range(num_runs):
        t_start = torch.cuda.Event(enable_timing=True)
        t_end = torch.cuda.Event(enable_timing=True)
        t_start.record()
        _ = func()
        t_end.record()
        torch.cuda.synchronize()
        res.append(t_start.elapsed_time(t_end) / 1000)
    return res


class SDRunner:
    def __init__(
        self,
        model_id,
        num_inference_steps,
        height,
        width,
        num_models,
        num_runs_per_model,
        use_tum,
        swap_memory,
    ):
        self.models = []
        for _ in range(num_models):
            model = create_diffusion_pipeline(
                task="text-to-image", model=model_id, revision=None, torch_compile=False
            )
            if swap_memory:
                model = model.to("cpu")
            model.set_progress_bar_config(disable=True)
            self.models.append(model)
        if use_tum:
            import tum

            tum.prefetch()
        self.prompt = "A photo of a cat"
        self.num_inference_steps = num_inference_steps
        self.height = height
        self.width = width
        self.num_runs_per_model = num_runs_per_model
        self.swap_memory = swap_memory

    def run(self):
        for model in self.models:
            if self.swap_memory:
                model = model.to("cuda")
            for _ in range(self.num_runs_per_model):
                _ = model(self.prompt, height=self.height, width=self.width)
            if self.swap_memory:
                model.to("cpu")
                # TODO: do we need to clear torch gpu caching allocator cache here?


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-m", "--model-id", type=str, default="stabilityai/stable-diffusion-2-1"
    )
    parser.add_argument("-S", "--num-inference-steps", type=int, default=50)
    parser.add_argument("-H", "--height", type=int, default=512)
    parser.add_argument("-W", "--width", type=int, default=512)
    parser.add_argument("-M", "--num-models", type=int, default=1)
    parser.add_argument("-r", "--num-runs-per-model", type=int, default=1)
    parser.add_argument("-w", "--num-warmup", type=int, default=1)
    parser.add_argument("-n", "--num-runs", type=int, default=10)
    parser.add_argument("-t", "--use-tum", action="store_true")
    parser.add_argument("-s", "--swap-memory", action="store_true")
    return parser.parse_args()


def main():
    print(f"Device: {torch.cuda.get_device_name(torch.cuda.current_device())}")

    args = parse_args()

    if args.use_tum:
        import tum

        tum.enable()

    runner = SDRunner(
        args.model_id,
        args.num_inference_steps,
        args.height,
        args.width,
        args.num_models,
        args.num_runs_per_model,
        args.use_tum,
        args.swap_memory,
    )

    res = benchmark(runner.run, args.num_warmup, args.num_runs)
    per_image_res = [x / args.num_models / args.num_runs_per_model for x in res]
    print(
        "Time (seconds) per image in each"
        f" run:\n{', '.join(str(round(x, 3)) for x in per_image_res)}"
    )
    print(
        "Average time (seconds) per image:"
        f" {(sum(per_image_res) / len(per_image_res)):.3f}"
    )


if __name__ == "__main__":
    main()
