from io import BytesIO
import os
from typing import List, Union
import warnings

from loguru import logger

from leptonai.config import TRUST_REMOTE_CODE
from leptonai.registry import Registry
from leptonai.photon import FileParam, HTTPException, get_file_content

from .hf_dependencies import hf_no_attention_mask_models

pipeline_registry = Registry()


def img_param_to_img(param: Union[str, bytes, FileParam]):
    warnings.warn(
        "img_param_to_img is deprecated and may be removed in a future version. To"
        " migrate, you should migrate your usage from FileParam to File."
    )
    from PIL import Image

    content = get_file_content(param)
    return Image.open(BytesIO(content))


def create_diffusion_pipeline(task, model, revision, torch_compile=False):
    try:
        from diffusers import DiffusionPipeline
        import torch
    except ImportError:
        raise RuntimeError(
            "Lepton huggingface photon requires torch and diffusers but they are not"
            " installed. Please install them with: pip install torch diffusers"
        )

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


def create_auto_image_to_image_pipeline(task, model, revision, torch_compile=False):
    try:
        from diffusers import AutoPipelineForImage2Image
        import torch
    except ImportError:
        raise RuntimeError(
            "Lepton huggingface photon requires torch and diffusers but they are not"
            " installed. Please install them with: pip install torch diffusers"
        )

    if torch.cuda.is_available():
        torch_dtype = torch.float16
    else:
        torch_dtype = torch.bfloat16

    try:
        pipeline = AutoPipelineForImage2Image.from_pretrained(
            model,
            revision=revision,
            torch_dtype=torch_dtype,
        )
    except Exception as e:
        logger.info(
            f"Failed to create pipeline with {torch_dtype}: {e}, fallback to fp32"
        )
        pipeline = AutoPipelineForImage2Image.from_pretrained(
            model,
            revision=revision,
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
    "image-to-image",
    create_auto_image_to_image_pipeline,
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
        pipe = pipeline(task, model=model, tokenizer=tokenizer)
    except Exception as e:
        raise ValueError(
            f"Failed to create pipeline with ggml for task={task}, model={model}: {e}"
        )
    else:
        return pipe


def _create_hf_transformers_pipeline(task, model, revision):
    from transformers import pipeline, AutoTokenizer, AutoConfig, AutoModelForCausalLM
    import torch

    kwargs = {}
    if TRUST_REMOTE_CODE:
        kwargs["trust_remote_code"] = TRUST_REMOTE_CODE

    # audio-classification pipeline doesn't support automatically
    # converting inputs from fp32 to fp16
    if torch.cuda.is_available() and task != "audio-classification":
        torch_dtype = torch.float16
    else:
        # TODO: check if bfloat16 is well supported
        torch_dtype = torch.float32

    kwargs["torch_dtype"] = torch_dtype

    model_kwargs = {
        "low_cpu_mem_usage": True,
    }

    if task == "text-generation":
        no_attention_mask = model in hf_no_attention_mask_models

        config = AutoConfig.from_pretrained(model, revision=revision, **kwargs)
        if no_attention_mask or not config.tokenizer_class:
            try:
                tokenizer = AutoTokenizer.from_pretrained(
                    model, revision=revision, **kwargs
                )
                if no_attention_mask:
                    # tokenizer checks if attention_mask is in
                    # model_input_names to set "return_attention_mask"
                    # kwargs
                    tokenizer.model_input_names.remove("attention_mask")

                    model_obj = AutoModelForCausalLM.from_pretrained(
                        model, revision=revision, **kwargs, **model_kwargs
                    )

                    def patch_model_obj(model_obj):
                        orig_generate = model_obj.generate

                        def no_attention_mask_generate(self, *args, **kwargs):
                            # remove attention_mask from kwargs
                            kwargs.pop("attention_mask", None)
                            return orig_generate(*args, **kwargs)

                        model_obj.generate = no_attention_mask_generate.__get__(
                            model_obj
                        )

                    patch_model_obj(model_obj)

                    if torch.cuda.is_available():
                        model_obj = model_obj.to("cuda")
            except Exception as e:
                logger.info(f"Failed to create tokenizer with AutoTokenizer: {e}")
            else:
                kwargs["tokenizer"] = tokenizer
                if no_attention_mask:
                    kwargs["model"] = model_obj

    if "model" not in kwargs:
        kwargs["model_kwargs"] = model_kwargs

    if torch.cuda.is_available():
        kwargs["device"] = 0
    kwargs.setdefault("model", model)
    try:
        pipe = pipeline(task=task, revision=revision, **kwargs)
    except Exception as e:
        logger.info(
            f"Failed to create pipeline with {torch_dtype}: {e}, fallback to fp32"
        )
        if "low_cpu_mem_usage" in str(e).lower():
            logger.info(
                "error seems to be caused by low_cpu_mem_usage, retry without"
                " low_cpu_mem_usage"
            )
            kwargs.get("model_kwargs", {}).pop("low_cpu_mem_usage")
            if not kwargs.get("model_kwargs"):
                kwargs.pop("model_kwargs")
        # fallback to fp32
        kwargs.pop("torch_dtype")
        pipe = pipeline(task=task, revision=revision, **kwargs)
    return pipe


def create_transformers_pipeline(task, model, revision):
    if task == "text-generation" and "ggml" in model.lower():
        return _create_ggml_transformers_pipeline(task, model, revision)
    else:
        return _create_hf_transformers_pipeline(task, model, revision)


for task in [
    "audio-classification",
    "automatic-speech-recognition",
    "depth-estimation",
    "feature-extraction",
    "image-classification",
    "image-to-text",
    "sentiment-analysis",
    "summarization",
    "text-classification",
    "text-generation",
    "text2text-generation",
    "token-classification",
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


def hf_missing_package_error_message(
    pipeline_name: str, missing_packages: List[str]
) -> str:
    return (
        "HuggingFace reported missing packages for the specified pipeline. You can see"
        " the hf error message above. \n\nThis is not a bug of LeptonAI, as"
        " HuggingFace pipelines do not have a standard way to pre-determine and"
        " install dependencies yet. As a best-effort attempt, here are steps you can"
        " take to fix this issue:\n\n1. If you are running locally, you can install"
        " the missing packages with pip as follows:\n\npip install"
        f" {' '.join(missing_packages)}\n\n(note that some package names and pip names"
        " may be different, and you may need to search pypi for the correct package"
        " name)\n\n2. If you are using LeptonAI library, we maintain a mapping from"
        " known HuggingFace pipelines to their dependencies. We appreciate if you can"
        " send a PR to https://github.com/leptonai/leptonai/ to add the missing"
        " dependencies. please refer to"
        " https://github.com/leptonai/leptonai/blob/main/leptonai/photon/hf/hf_dependencies.py"
        " for more details."
    )


def hf_try_explain_run_exception(e: Exception) -> Exception:
    """
    Try to categorize the exception and provide a more user-friendly error message.
    """
    if isinstance(e, TypeError):
        if "'NoneType' object is not callable" in str(e):
            new_e = HTTPException(
                status_code=503,
                detail=(
                    "Your pipeline encountered a runtime error that is known to not be"
                    " a bug of LeptonAI. Specifically, the text generation pipeline"
                    " that you are running did not specify tokenizer_class in its"
                    " model's config.json file, and causing the pipeline to not be able"
                    " to automatically determine the tokenizer class. If you are the"
                    " author of the pipeline, consider adding tokenizer_class to your"
                    " model's config.json file."
                ),
            )
            new_e.__cause__ = e
            return new_e
    # Finall falback: return the original exception
    return e
