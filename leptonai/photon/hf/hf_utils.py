import base64
import os
import tempfile

from loguru import logger

from leptonai.registry import Registry
from leptonai.photon import FileParam

pipeline_registry = Registry()


def img_param_to_img(param):
    from diffusers.utils import load_image

    if isinstance(param, FileParam):
        file = tempfile.NamedTemporaryFile()
        file.write(param.file.read())
        file.flush()
        param = file.name
    elif isinstance(param, str):
        if param.startswith("http://") or param.startswith("https://"):
            pass
        else:
            # base64
            file = tempfile.NamedTemporaryFile()
            file.write(base64.b64decode(param.encode("ascii")))
            file.flush()
            param = file.name
    else:
        raise ValueError(f"Invalid image param: {param}")
    image = load_image(param)
    return image


def create_diffusion_pipeline(task, model, revision, torch_compile=False):
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


def _create_ggml_transformers_pipeline(task, model, revision):
    try:
        import ctransformers  # noqa: F401
    except ImportError:
        raise ValueError(
            "Failed to import ctransformers, please install it with: pip install"
            " ctransformers"
        )
    from ctransformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig
    from ctransformers.lib import load_cuda
    from transformers import pipeline

    kwargs = {
        "hf": True,
    }

    config = AutoConfig.from_pretrained(model, revision=revision)
    if config.model_type:
        model_type = config.model_type
    else:
        # infer model_type from model name
        if "llama" in model.lower():
            model_type = "llama"
        elif "falcon" in model.lower():
            model_type = "falcon"
        else:
            raise ValueError(f"Failed to infer ggml model_type from model={model}")
    kwargs["model_type"] = model_type
    if os.environ.get("HF_GGML_MODEL_FILE"):
        kwargs["model_file"] = os.environ["HF_GGML_MODEL_FILE"]

    if load_cuda():
        # set a sufficiently large number to indicate all layers are on gpu
        kwargs["gpu_layers"] = 9999999

    try:
        model = AutoModelForCausalLM.from_pretrained(model, revision=revision, **kwargs)
        tokenizer = AutoTokenizer.from_pretrained(model)
        pipeline = pipeline(task, model=model, tokenizer=tokenizer)
    except Exception as e:
        raise ValueError(
            f"Failed to create pipeline with ggml for task={task}, model={model}: {e}"
        )
    else:
        return pipeline


def _create_hf_transformers_pipeline(task, model, revision):
    from transformers import pipeline
    import torch

    kwargs = {"trust_remote_code": True}
    if torch.cuda.is_available():
        kwargs["device"] = 0

    # audio-classification pipeline doesn't support automatically
    # converting inputs from fp32 to fp16
    if torch.cuda.is_available() and task != "audio-classification":
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


def create_transformers_pipeline(task, model, revision):
    if task == "text-generation" and "ggml" in model.lower():
        return _create_ggml_transformers_pipeline(task, model, revision)
    else:
        return _create_hf_transformers_pipeline(task, model, revision)


for task in [
    "audio-classification",
    "automatic-speech-recognition",
    "depth-estimation",
    "sentiment-analysis",
    "summarization",
    "text-classification",
    "text-generation",
    "text2text-generation",
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
