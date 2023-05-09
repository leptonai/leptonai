from abc import ABC, abstractmethod
import functools
import cloudpickle
from io import BytesIO
import importlib
import inspect
import os
from typing import Callable, Any

from fastapi import FastAPI, Request, APIRouter
from loguru import logger
import pydantic
from fastapi.responses import JSONResponse, Response, StreamingResponse
import uvicorn

from .base import Photon, schema_registry

schemas = ["py"]


def send_file(content, media_type):
    return StreamingResponse(content=content, media_type=media_type)


def send_pil_img(pil_img):
    img_io = BytesIO()
    pil_img.save(img_io, "PNG", quality="keep")
    img_io.seek(0)
    return send_file(img_io, media_type="image/png")


def create_model_for_func(func: Callable):
    (
        args,
        _,
        varkw,
        defaults,
        kwonlyargs,
        kwonlydefaults,
        annotations,
    ) = inspect.getfullargspec(func)
    if len(args) > 0 and args[0] == "self" or args[0] == "cls":
        args = args[1:]  # remove self or cls
    if defaults is None:
        defaults = ()
    non_default_args_count = len(args) - len(defaults)
    defaults = (...,) * non_default_args_count + defaults

    keyword_only_params = {
        param: kwonlydefaults.get(param, Any) for param in kwonlyargs
    }
    params = {
        param: (annotations.get(param, Any), default)
        for param, default in zip(args, defaults)
    }

    if varkw:

        class config:
            extra = "allow"

    else:
        config = None

    InputModel = pydantic.create_model(
        f"Input",
        **params,
        **keyword_only_params,
        __config__=config,
    )

    return_type = inspect.signature(func).return_annotation
    if return_type is inspect.Signature.empty:
        return_type = Any

    class Config:
        arbitrary_types_allowed = True

    OutputModel = pydantic.create_model(
        f"Output",
        input=InputModel,
        output=(return_type, None),
        __config__=Config,
    )
    return InputModel, OutputModel


_routes = {}


def get_routes(var):
    qualname = var.__qualname__
    if not inspect.isclass(var):
        qualname = ".".join(qualname.split(".")[:-1])
    cls_name = f"{var.__module__}.{qualname}"
    if cls_name not in _routes:
        _routes[cls_name] = {}
    return _routes[cls_name]


class RunnerPhoton(Photon):
    photon_type: str = "runner"
    obj_pkl_filename: str = "obj.pkl"

    image: str = "lepton:photon-py-runner"
    args: list = ["--shm-size=1g"]

    def __init__(self, name=None, model=None):
        if name is None:
            name = self.__class__.__qualname__
        if model is None:
            model = self.__class__.__qualname__
        super().__init__(name=name, model=model)
        self.routes = get_routes(self.__class__)
        self._init_called = False
        self._init_res = None

    @staticmethod
    def get_pip_deps():
        # ref: https://stackoverflow.com/a/31304042
        try:
            from pip._internal.operations import freeze
        except ImportError:  # pip < 10.0
            from pip.operations import freeze

        pkgs = freeze.freeze()

        filtered_pkgs = []
        for pkg in pkgs:
            if pkg.startswith("-e"):
                # TODO: capture local editable packages
                continue
            if pkg.startswith(f"pytest"):
                continue
            filtered_pkgs.append(pkg)
        return filtered_pkgs

    @property
    def metadata(self):
        res = super().metadata

        res["routes"] = {}
        for path, (func, response_class) in self.routes.items():
            method = func.__get__(self, self.__class__)
            request_type, repsonse_type = create_model_for_func(method)
            res["routes"][path] = {
                "path": path,
                "handler_name": method.__name__,
                "input_model": request_type.schema(),
                "output_model": repsonse_type.schema(),
            }

        res["py_obj"] = {
            "name": self.__class__.__qualname__,
            "obj_pkl_file": self.obj_pkl_filename,
        }

        try:
            requirement_dependency = self.get_pip_deps()
        except Exception as e:
            logger.warning(f"Failed to get pip dependencies: {e}")
            requirement_dependency = []
        res.update({"requirement_dependency": self.get_pip_deps()})

        res.update(
            {
                "image": self.image,
                "args": self.args,
            }
        )

        return res

    @property
    def extra_files(self):
        res = super().extra_files
        res.update(
            {
                self.obj_pkl_filename: cloudpickle.dumps(self),
            }
        )
        return res

    @classmethod
    def load(cls, photon_file, metadata):
        obj_pkl_filename = metadata["py_obj"]["obj_pkl_file"]
        py_obj = cloudpickle.loads(photon_file.open(obj_pkl_filename).read())
        return py_obj

    def init(self):
        pass

    def call_init(self):
        if not self._init_called:
            self._init_res = self.init()
            self._init_called = True
        return self._init_res

    @abstractmethod
    def run(self, *args, **kwargs):
        raise NotImplementedError

    def launch(self, host="0.0.0.0", port=8080, log_level="info"):
        self.call_init()

        title = self.name.replace(".", "_")
        app = FastAPI(title=title)
        self._register_routes(app)
        return uvicorn.run(app, host=host, port=port, log_level=log_level)

    def _register_routes(self, app):
        api_router = APIRouter()
        for path, (func, response_class) in self.routes.items():

            def create_typed_handler(func, response_class):
                method = func.__get__(self, self.__class__)
                request_type, reponse_type = create_model_for_func(method)
                vd = pydantic.decorator.ValidatedFunction(method, None)

                async def typed_handler(request: request_type):
                    logger.info(request)
                    try:
                        res = vd.execute(request)
                    except Exception as e:
                        logger.error(e)
                        return JSONResponse({"error": str(e)}, status_code=500)
                    else:
                        if not isinstance(res, Response):
                            res = JSONResponse(res)
                        return res

                if response_class is None:
                    kwargs = {"response_model": reponse_type}
                else:
                    kwargs = {"response_class": response_class}

                return typed_handler, kwargs

            typed_handler, kwargs = create_typed_handler(func, response_class)
            api_router.add_api_route(
                f"/{path}", typed_handler, methods=["POST"], **kwargs
            )
        app.include_router(api_router)

    @staticmethod
    def handler(path=None, response_class=None):
        def decorator(func):
            path_ = path or func.__name__
            routes = get_routes(func)
            if path_ in routes:
                raise ValueError(f"Path {path_} already exists: {routes[path_]}")

            @functools.wraps(func)
            def wrapped_func(self, *args, **kwargs):
                self.call_init()
                return func(self, *args, **kwargs)

            routes[path_] = (func, response_class)
            return wrapped_func

        return decorator

    @classmethod
    def create_from_model_str(cls, name, model_str):
        model_parts = model_str.split(":")
        if len(model_parts) != 3 or model_parts[0] not in schemas:
            raise ValueError(f"Unsupported Python model string: {model_str}")
        path, cls_name = model_parts[1:]
        path_parts = os.path.splitext(os.path.basename(path))
        if len(path_parts) != 2 or path_parts[1] != ".py":
            raise ValueError(f"File path should be a Python file (.py): {path}")
        module_name = path_parts[0]
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None:
            raise ValueError(f"Could not import Python module from path: {path}")
        module = importlib.util.module_from_spec(spec)
        if spec.loader is None:
            raise ValueError(f"Could not import Python module from path: {path}")
        spec.loader.exec_module(module)
        runner_cls = getattr(module, cls_name)
        if not inspect.isclass(runner_cls) or not issubclass(runner_cls, cls):
            raise ValueError(f"{cls_name} is not a sub class of {cls.__name__}")
        runner = runner_cls(name=name, model=model_str)
        return runner


handler = RunnerPhoton.handler


schema_registry.register(schemas, RunnerPhoton.create_from_model_str)
