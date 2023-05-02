from io import BytesIO
import logging

from loguru import logger
from flask import Flask, request, send_file, abort
from werkzeug.datastructures import FileStorage

from lepton.registry import Registry


class _HuggingfaceRunner:
    pass


pipeline_registry = Registry()
server_preprocessor_registry = Registry()
server_postprocessor_registry = Registry()


class HuggingfaceInProcessRunner(_HuggingfaceRunner):
    def __init__(self, photon):
        pipeline_creator = pipeline_registry.get(photon.hf_task)
        logging.info(
            f"Creating pipeline for {photon.hf_task}(model={photon.hf_model}, revision={photon.hf_revision}"
        )
        self.pipeline = pipeline_creator(
            task=photon.hf_task,
            model=photon.hf_model,
            revision=photon.hf_revision,
        )

    def run(self, *args, **kwargs):
        return self.pipeline(*args, **kwargs)


class HuggingfaceServerRunner(_HuggingfaceRunner):
    image: str = "lepton:photon-hf-runner"
    args: list = ["--shm-size=1g"]

    def __init__(self, photon, port=8080):
        self.photon = photon
        self.port = port

        self._app = Flask(self.photon.name.replace(".", "-"))
        self._preprocessor = server_preprocessor_registry.get(self.photon.hf_task)
        self._postprocessor = server_postprocessor_registry.get(self.photon.hf_task)

        self._app.post("/run")(self._run)

    def run(self):
        self._app.logger.setLevel(logging.INFO)
        return self._app.run(host="0.0.0.0", port=self.port)

    def _run(self):
        # TODO: check bearer token
        if request.files:
            self._app.logger.info(f"request.files={request.files}")
            data = {}
            files_dict = request.files.to_dict(flat=False)
            for k, v in files_dict.items():
                if len(v) == 1:
                    v = v[0]
                data[k] = v
            if request.form:
                form_dict = request.form.to_dict(flat=False)
                for k, v in form_dict.items():
                    if k in data:
                        return abort(400, f"Mixed files and form data for key {k}")
                    if len(v) == 1:
                        v = v[0]
                    data[k] = v
        else:
            try:
                data = request.get_json(force=True)
            except Exception as e:
                if request.is_json:
                    return abort(400, "Invalid json format data")
                self._app.logger.info(e)
                data = {}
        self._app.logger.info(f"data={data}")

        if not data:
            return abort(400, "Empty input")

        try:
            args, kwargs = self._preprocessor(data)
            res = self.photon.run(*args, **kwargs)
            res = self._postprocessor(res)
        except Exception as e:
            self._app.logger.warn(e)
            return abort(400, str(e))
        else:
            self._app.logger.info(f"res={res}")
            return res


def send_pil_img(pil_img):
    img_io = BytesIO()
    pil_img.save(img_io, "PNG", quality="keep")
    img_io.seek(0)
    return send_file(img_io, mimetype="image/png")


def diffusion_pipeline_preprocessor(data):
    return [], data


server_preprocessor_registry.register("text-to-image", diffusion_pipeline_preprocessor)


def cast_data_val(data, from_type, caster):
    def cast_val(v):
        if isinstance(v, from_type):
            return caster(v)
        elif isinstance(v, list):
            return [cast_val(v2) for v2 in v]
        elif isinstance(v, dict):
            return {k: cast_val(v2) for k, v2 in v.items()}
        else:
            return v

    return {k: cast_val(v) for k, v in data.items()}


def transformers_asr_preprocessor(data):
    import numpy as np

    # from transformers `AutomaticSpeechRecognitionPipeline` doc,
    # inputs can be np.ndarray
    data = cast_data_val(data, FileStorage, lambda f: np.fromfile(f, dtype=np.uint8))

    return [], data


server_preprocessor_registry.register(
    "automatic-speech-recognition", transformers_asr_preprocessor
)


def transformers_texts_tasks_preprocessor(data):
    if "inputs" not in data:
        raise ValueError("Missing 'inputs' field in request data")

    inputs = data.pop("inputs")
    return [inputs], data


server_preprocessor_registry.register(
    "text-generation", transformers_texts_tasks_preprocessor
)


def diffusion_pipeline_postprocessor(res):
    return send_pil_img(res.images[0])


def no_op_postprocessor(res):
    return res


server_postprocessor_registry.register(
    "text-to-image", diffusion_pipeline_postprocessor
)

for task in ["text-generation", "automatic-speech-recognition"]:
    server_postprocessor_registry.register(task, no_op_postprocessor)


def create_diffusion_pipeline(task, model, revision):
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
    kwargs = {'trust_remote_code': True}
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


for task in ["text-generation", "automatic-speech-recognition"]:
    pipeline_registry.register(
        task,
        create_transformers_pipeline,
    )


class HuggingfaceClusterrunner(_HuggingfaceRunner):
    # TODO: implement
    pass
