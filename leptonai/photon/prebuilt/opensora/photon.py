import io
import os
import tempfile
import uuid
from datetime import datetime

from typing import List, Optional
from rich.pretty import Pretty
from loguru import logger

from leptonai.api.v0 import workspace
from leptonai.photon import Photon, Worker, get_file_content
from leptonai.api.v1.client import APIClient


class OpenSora(Worker):
    queue_name = "open-sora"
    kv_name = "open-sora"

    requirement_dependency = []
    health_check_liveness_tcp_port = 8765
    image = "leptonai/opensora:latest"
    config = {
        "resolution": "720p",
        "aspect_ratio": "9:16",
        "num_frames": 384,
        "fps": 24,
        "frame_interval": 1,
        "save_fps": 24,
        "save_dir": "./samples/samples/",
        "seed": 42,
        "batch_size": 1,
        "multi_resolution": "STDiT2",
        "dtype": "bf16",
        "condition_frame_length": 5,
        "align": 5,
        "model": {
            "type": "STDiT3-XL/2",
            "from_pretrained": "hpcai-tech/OpenSora-STDiT-v3",
            "qk_norm": True,
            "enable_flash_attn": True,
            "enable_layernorm_kernel": True,
        },
        "vae": {
            "type": "OpenSoraVAE_V1_2",
            "from_pretrained": "hpcai-tech/OpenSora-VAE-v1.2",
            "micro_frame_size": 17,
            "micro_batch_size": 4,
        },
        "text_encoder": {
            "type": "t5",
            "from_pretrained": "DeepFloyd/t5-v1_1-xxl",
            "model_max_length": 300,
        },
        "scheduler": {
            "type": "rflow",
            "use_timestep_transform": True,
            "num_sampling_steps": 30,
            "cfg_scale": 7.0,
        },
        "aes": 6.5,
        "flow": None,
    }

    OPENSORA_OBJECTSTORE_OUTPUT_PREFIX = "opensora/output"

    def init(self):

        import colossalai
        import torch
        import torch.distributed as dist
        from colossalai.cluster import DistCoordinator
        from mmengine.runner import set_random_seed

        from opensora.acceleration.parallel_states import set_sequence_parallel_group
        from opensora.datasets.aspect import get_image_size, get_num_frames
        from opensora.registry import MODELS, SCHEDULERS, build_module
        from opensora.utils.misc import is_distributed, to_torch_dtype
        from mmengine.config import Config

        workspace.login()

        cfg = Config(self.config)

        bucket = os.environ.get("OBJECTSTORE_BUCKET", "private")
        logger.info(f"Using bucket {bucket}")
        self._is_public_bucket = bucket.lower() == "public"

        # == device and dtype ==
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = to_torch_dtype("bf16")
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True

        # == init distributed env ==
        if is_distributed():
            colossalai.launch_from_torch({})
            coordinator = DistCoordinator()
            enable_sequence_parallelism = coordinator.world_size > 1
            if enable_sequence_parallelism:
                set_sequence_parallel_group(dist.group.WORLD)
        else:
            coordinator = None
            enable_sequence_parallelism = False
        self.coordinator = coordinator
        self.enable_sequence_parallelism = enable_sequence_parallelism
        set_random_seed(1024)

        num_frames = cfg["num_frames"]
        image_size = get_image_size(cfg["resolution"], cfg["aspect_ratio"])
        num_frames = get_num_frames(num_frames)

        # == init logger ==
        logger.info("Inference configuration:\n %s", Pretty(cfg.to_dict()))

        # ======================================================
        # build model & load weights
        # ======================================================
        logger.info("Building models...")

        self.vae = build_module(cfg.vae, MODELS).to(self.device, self.dtype).eval()
        self.text_encoder = build_module(cfg.text_encoder, MODELS, device=self.device)
        input_size = (num_frames, *image_size)
        latent_size = self.vae.get_latent_size(input_size)

        self.model = (
            build_module(
                cfg.model,
                MODELS,
                input_size=latent_size,
                in_channels=self.vae.out_channels,
                caption_channels=self.text_encoder.output_dim,
                model_max_length=self.text_encoder.model_max_length,
                enable_sequence_parallelism=self.enable_sequence_parallelism,
            )
            .to(self.device, self.dtype)
            .eval()
        )
        self.text_encoder.y_embedder = self.model.y_embedder
        self.scheduler = build_module(cfg.scheduler, SCHEDULERS)

        self.save_dir = cfg.save_dir

        super().init()

    def on_task(
        self,
        task_id: str,
        fps,
        multi_resolution,
        prompts,
        batch_size,
        mask_strategy,
        reference_path,
        num_sample,
        save_fps,
        resolution,
        length,
        aspect_ratio,
        llm_refine=None,
        aes=None,
        flow=None,
        camera_motion=None,
        prompt_as_path=False,
        loop=1,
        condition_frame_length=5,
        condition_frame_edit=0.0,
        align=None,
        image=None,
    ):
        from tqdm import tqdm

        from opensora.datasets import save_sample
        from opensora.models.text_encoder.t5 import text_preprocessing
        from opensora.utils.inference_utils import (
            append_generated,
            append_score_to_prompts,
            apply_mask_strategy,
            collect_references_batch,
            dframe_to_frame,
            extract_json_from_prompts,
            extract_prompts_loop,
            get_save_path_name,
            merge_prompt,
            prepare_multi_resolution_info,
            refine_prompts_by_openai,
            split_prompt,
        )
        from opensora.datasets.aspect import get_image_size, get_num_frames
        from opensora.utils.misc import all_exists, is_main_process
        import torch
        import torch.distributed as dist
        from diffusers.utils import load_image

        logger.info(
            "on_task called at {time} | task_id: {task_id}, fps: {fps},"
            " multi_resolution: {multi_resolution}, batch_size: {batch_size},"
            " mask_strategy: {mask_strategy}, reference_path: {reference_path},"
            " num_sample: {num_sample}, save_fps: {save_fps}, llm_refine: {llm_refine},"
            " aes: {aes}, flow: {flow}, camera_motion: {camera_motion}, prompt_as_path:"
            " {prompt_as_path}, loop: {loop}, condition_frame_length:"
            " {condition_frame_length}, condition_frame_edit: {condition_frame_edit},"
            " align: {align}, prompt: {prompts}resolution: {resolution}, length:"
            " {length},aspect_ratio: {aspect_ratio}",
            time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            task_id=task_id,
            fps=fps,
            multi_resolution=multi_resolution,
            batch_size=batch_size,
            mask_strategy=mask_strategy,
            reference_path=reference_path,
            num_sample=num_sample,
            save_fps=save_fps,
            llm_refine=llm_refine,
            aes=aes,
            flow=flow,
            camera_motion=camera_motion,
            prompt_as_path=prompt_as_path,
            loop=loop,
            condition_frame_length=condition_frame_length,
            condition_frame_edit=condition_frame_edit,
            align=align,
            prompts=prompts,
            resolution=resolution,
            length=length,
            aspect_ratio=aspect_ratio,
        )

        torch.set_grad_enabled(False)

        key_list = []

        if image:
            if isinstance(image, tuple):
                bucket, key = image
                response = APIClient().objectstore.get(key, bucket, return_url=True)
                url = response.headers.get("Location")
                image = url
            _, ext = os.path.splitext(image)
            image = load_image(image)
            temp_file = tempfile.NamedTemporaryFile(suffix=ext.lower())
            image.save(temp_file.name)
            image_name = temp_file.name
            reference_path = [image_name] * len(prompts)

        image_size = get_image_size(resolution, aspect_ratio)
        num_frames = get_num_frames(length)
        input_size = (num_frames, *image_size)
        latent_size = self.vae.get_latent_size(input_size)
        # == Iter over all samples ==
        with tempfile.TemporaryDirectory() as temp_dir:

            for i in tqdm(range(0, len(prompts), batch_size)):
                # == prepare batch prompts ==
                batch_prompts = prompts[i : i + batch_size]
                ms = mask_strategy[i : i + batch_size]
                refs = reference_path[i : i + batch_size]

                # == get json from prompts ==
                batch_prompts, refs, ms = extract_json_from_prompts(
                    batch_prompts, refs, ms
                )
                original_batch_prompts = batch_prompts

                # == get reference for condition ==
                refs = collect_references_batch(refs, self.vae, image_size)

                # == multi-resolution info ==
                model_args = prepare_multi_resolution_info(
                    multi_resolution,
                    len(batch_prompts),
                    image_size,
                    num_frames,
                    fps,
                    self.device,
                    self.dtype,
                )

                # == Iter over number of sampling for one prompt ==

                start_idx = 0
                for k in range(num_sample):
                    # == prepare save paths ==
                    save_paths = [
                        get_save_path_name(
                            temp_dir,
                            sample_name=task_id + str(start_idx) + str(idx),
                            sample_idx=start_idx + idx,
                            prompt=original_batch_prompts[idx],
                            prompt_as_path=prompt_as_path,
                            num_sample=num_sample,
                            k=k,
                        )
                        for idx in range(len(batch_prompts))
                    ]

                    # NOTE: Skip if the sample already exists
                    # This is useful for resuming sampling VBench
                    if prompt_as_path and all_exists(save_paths):
                        continue

                    # == process prompts step by step ==
                    # 0. split prompt
                    # each element in the list is [prompt_segment_list, loop_idx_list]
                    batched_prompt_segment_list = []
                    batched_loop_idx_list = []
                    for prompt in batch_prompts:
                        prompt_segment_list, loop_idx_list = split_prompt(prompt)
                        batched_prompt_segment_list.append(prompt_segment_list)
                        batched_loop_idx_list.append(loop_idx_list)

                    # 1. refine prompt by openai
                    if llm_refine:
                        # only call openai API when
                        # 1. seq parallel is not enabled
                        # 2. seq parallel is enabled and the process is rank 0
                        if not self.enable_sequence_parallelism or (
                            self.enable_sequence_parallelism and is_main_process()
                        ):
                            for idx, prompt_segment_list in enumerate(
                                batched_prompt_segment_list
                            ):
                                batched_prompt_segment_list[idx] = (
                                    refine_prompts_by_openai(prompt_segment_list)
                                )

                        # sync the prompt if using seq parallel
                        if self.enable_sequence_parallelism:
                            self.coordinator.block_all()
                            prompt_segment_length = [
                                len(prompt_segment_list)
                                for prompt_segment_list in batched_prompt_segment_list
                            ]

                            # flatten the prompt segment list
                            batched_prompt_segment_list = [
                                prompt_segment
                                for prompt_segment_list in batched_prompt_segment_list
                                for prompt_segment in prompt_segment_list
                            ]

                            # create a list of size equal to world size
                            broadcast_obj_list = [
                                batched_prompt_segment_list
                            ] * self.coordinator.world_size
                            dist.broadcast_object_list(broadcast_obj_list, 0)

                            # recover the prompt list
                            batched_prompt_segment_list = []
                            segment_start_idx = 0
                            all_prompts = broadcast_obj_list[0]
                            for num_segment in prompt_segment_length:
                                batched_prompt_segment_list.append(
                                    all_prompts[
                                        segment_start_idx : segment_start_idx
                                        + num_segment
                                    ]
                                )
                                segment_start_idx += num_segment

                    # 2. append score
                    for idx, prompt_segment_list in enumerate(
                        batched_prompt_segment_list
                    ):
                        batched_prompt_segment_list[idx] = append_score_to_prompts(
                            prompt_segment_list,
                            aes=aes,
                            flow=flow,
                            camera_motion=camera_motion,
                        )

                    # 3. clean prompt with T5
                    for idx, prompt_segment_list in enumerate(
                        batched_prompt_segment_list
                    ):
                        batched_prompt_segment_list[idx] = [
                            text_preprocessing(prompt) for prompt in prompt_segment_list
                        ]

                    # 4. merge to obtain the final prompt
                    batch_prompts = []
                    for prompt_segment_list, loop_idx_list in zip(
                        batched_prompt_segment_list, batched_loop_idx_list
                    ):
                        batch_prompts.append(
                            merge_prompt(prompt_segment_list, loop_idx_list)
                        )

                    # == Iter over loop generation ==
                    video_clips = []
                    for loop_i in range(loop):
                        # == get prompt for loop i ==
                        batch_prompts_loop = extract_prompts_loop(batch_prompts, loop_i)

                        # == add condition frames for loop ==
                        if loop_i > 0:
                            refs, ms = append_generated(
                                self.vae,
                                video_clips[-1],
                                refs,
                                ms,
                                loop_i,
                                condition_frame_length,
                                condition_frame_edit,
                            )

                        # == sampling ==
                        torch.manual_seed(1024)
                        z = torch.randn(
                            len(batch_prompts),
                            self.vae.out_channels,
                            *latent_size,
                            device=self.device,
                            dtype=self.dtype,
                        )
                        masks = apply_mask_strategy(z, refs, ms, loop_i, align=align)

                        samples = self.scheduler.sample(
                            self.model,
                            self.text_encoder,
                            z=z,
                            prompts=batch_prompts_loop,
                            device=self.device,
                            additional_args=model_args,
                            progress=False,
                            mask=masks,
                        )
                        samples = self.vae.decode(
                            samples.to(self.dtype), num_frames=num_frames
                        )
                        video_clips.append(samples)

                    # == save samples ==
                    if is_main_process():
                        for idx, batch_prompt in enumerate(batch_prompts):
                            save_path = save_paths[idx]
                            key = os.path.basename(save_path)
                            video = [video_clips[i][idx] for i in range(loop)]
                            for j in range(1, loop):
                                video[j] = video[j][
                                    :, dframe_to_frame(condition_frame_length) :
                                ]
                            video = torch.cat(video, dim=1)
                            save_path = save_sample(
                                video,
                                fps=save_fps,
                                save_path=save_path,
                                verbose=False,
                            )
                            logger.info(
                                f"Uploading output to {self._is_public_bucket}/{key}"
                            )
                            with open(save_path, "rb") as f:
                                APIClient().object_storage.put(
                                    key, f, self._is_public_bucket
                                )
                            key_list.append(key)

                start_idx += len(batch_prompts)

        logger.info("Inference finished.")

        return {"bucket": self._is_public_bucket, "keys": key_list}

    @Photon.handler
    def run(
        self,
        prompts: List[str],
        text_to_image: bool = False,
        save_fps: int = 24,
        batch_size: int = 1,
        num_sample: int = 1,
        loop: int = 1,
        condition_frame_length: int = 5,
        condition_frame_edit: float = 0.0,
        align: int = 5,
        aes: float = 6.5,
        multi_resolution: str = "STDiT2",
        reference_path: Optional[List[str]] = None,
        mask_strategy: Optional[List[str]] = None,
        llm_refine: bool = False,
        flow: Optional[float] = None,
        camera_motion: Optional[str] = None,
        prompt_as_path: Optional[bool] = None,
        # from gradio (UI specific parameters)
        resolution: str = "720p",
        length: str = "4s",
        aspect_ratio: str = "9:16",
        image: Optional[str] = None,
        fps: int = 24,
    ):
        logger.info(
            "run called at {time} with parameters | fps: {fps}, multi_resolution:"
            " {multi_resolution}, batch_size: {batch_size}, num_sample: {num_sample},"
            " loop: {loop},condition_frame_length: {condition_frame_length},"
            " condition_frame_edit: {condition_frame_edit}, align: {align}, aes: {aes},"
            " mask_strategy: {mask_strategy}, reference_path: {reference_path},"
            " save_fps: {save_fps}, llm_refine: {llm_refine}, flow: {flow},"
            " camera_motion: {camera_motion}, prompt_as_path: {prompt_as_path},"
            " prompts: {prompts}, resolution: {resolution}, length:"
            " {length},aspect_ratio: {aspect_ratio}",
            time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            fps=fps,
            multi_resolution=multi_resolution,
            batch_size=batch_size,
            num_sample=num_sample,
            loop=loop,
            condition_frame_length=condition_frame_length,
            condition_frame_edit=condition_frame_edit,
            align=align,
            aes=aes,
            mask_strategy=mask_strategy,
            reference_path=reference_path,
            save_fps=save_fps,
            llm_refine=llm_refine,
            flow=flow,
            camera_motion=camera_motion,
            prompt_as_path=prompt_as_path,
            prompts=prompts,
            resolution=resolution,
            length=length,
            aspect_ratio=aspect_ratio,
        )

        reference_path = reference_path or [""] * len(prompts)
        mask_strategy = mask_strategy or [""] * len(prompts)

        if not text_to_image and image:
            mask_strategy = ["0"] * len(prompts)

        assert len(reference_path) == len(
            prompts
        ), "Length of reference must be the same as prompts"
        assert len(mask_strategy) == len(
            prompts
        ), "Length of mask_strategy must be the same as prompts"

        if image and (image.startswith("http://") or image.startswith("https://")):
            image = image
        elif image:
            logger.info(f"image is not a url, uploading to {self._bucket}")
            # Load the conditioning image
            image_bytes = get_file_content(image)
            image_io = io.BytesIO(image_bytes)

            key = f"{self.OBJECTSTORE_INPUT_PREFIX}/{uuid.uuid4()}"
            try:
                APIClient().objectstore.put(key, image_io, self._bucket)
            except Exception as e:
                logger.error(f"Failed to upload input to {self._bucket}/{key}: {e}")
                raise
            else:
                logger.info(f"Uploaded input to {self._bucket}/{key}")

            if self._is_public_bucket:
                response = self.objectstore.get(
                    key=key, is_public=self._is_public_bucket, return_url=True
                )
                url = response.headers.get("Location")
                image = url
            else:
                image = {"bucket": self._bucket, "key": key}

        return self.task_post({
            "fps": fps,
            "multi_resolution": multi_resolution,
            "prompts": prompts,
            "batch_size": batch_size,
            "mask_strategy": mask_strategy,
            "reference_path": reference_path,
            "num_sample": num_sample,
            "save_fps": save_fps,
            "llm_refine": llm_refine,
            "aes": aes,
            "flow": flow,
            "camera_motion": camera_motion,
            "prompt_as_path": prompt_as_path,
            "loop": loop,
            "condition_frame_length": condition_frame_length,
            "condition_frame_edit": condition_frame_edit,
            "align": align,
            "resolution": resolution,
            "length": length,
            "aspect_ratio": aspect_ratio,
            "image": image,
        })
