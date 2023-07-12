from loguru import logger

from leptonai.registry import Registry

pipeline_registry = Registry()


def create_diffusion_pipeline(task, model, revision, torch_compile=True):
    from diffusers import DiffusionPipeline, DPMSolverMultistepScheduler
    import torch

    if torch.cuda.is_available():
        torch_dtype = torch.float16
    else:
        torch_dtype = torch.bfloat16

    try:
        pipeline = DiffusionPipeline.from_pretrained(
            model,
            revision=revision,
            torch_dtype=torch_dtype,
        )
    except Exception as e:
        logger.info(
            f"Failed to create pipeline with {torch_dtype}: {e}, fallback to fp32"
        )
        pipeline = DiffusionPipeline.from_pretrained(
            model,
            revision=revision,
        )
    pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
        pipeline.scheduler.config
    )
    if torch.cuda.is_available():
        pipeline = pipeline.to("cuda")
        if torch_compile:
            try:
                torch._dynamo.config.suppress_errors = True
                pipeline.unet = torch.compile(
                    pipeline.unet, mode="reduce-overhead", fullgraph=True
                )
            except Exception as e:
                device_name = torch.cuda.get_device_name(torch.cuda.current_device())
                torch_version = torch.__version__
                logger.info(
                    f"Failed to enable torch.compile on device_name={device_name},"
                    f" torch_version={torch_version}: {e}"
                )
            else:
                logger.info("Enabled torch.compile")
    return pipeline


pipeline_registry.register(
    "text-to-image",
    create_diffusion_pipeline,
)


def create_transformers_pipeline(task, model, revision):
    from transformers import pipeline
    import torch

    # TODO: dolly model needs it. however we need to check if it's
    # safe to enable it for all models
    kwargs = {"trust_remote_code": True}
    if torch.cuda.is_available():
        kwargs["device"] = 0

    if torch.cuda.is_available():
        torch_dtype = torch.float16
    else:
        # TODO: check if bfloat16 is well supported
        torch_dtype = torch.float32

    try:
        # try fp16
        kwargs["torch_dtype"] = torch_dtype
        pipeline = pipeline(task=task, model=model, revision=revision, **kwargs)
    except Exception as e:
        logger.info(
            f"Failed to create pipeline with {torch_dtype}: {e}, fallback to fp32"
        )
        # fallback to fp32
        kwargs.pop("torch_dtype")
        pipeline = pipeline(task=task, model=model, revision=revision, **kwargs)
    return pipeline


for task in [
    "text-generation",
    "text2text-generation",
    "automatic-speech-recognition",
    "summarization",
]:
    pipeline_registry.register(
        task,
        create_transformers_pipeline,
    )


def create_sentence_transformers_pipeline(task, model, revision):
    from sentence_transformers import SentenceTransformer
    import torch

    kwargs = {}
    if torch.cuda.is_available():
        kwargs["device"] = 0

    st_model = SentenceTransformer(model, **kwargs)
    return st_model.encode


pipeline_registry.register("sentence-similarity", create_sentence_transformers_pipeline)
