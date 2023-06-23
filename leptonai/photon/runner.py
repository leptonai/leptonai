from abc import abstractmethod
import copy
import functools
import cloudpickle
import importlib
import inspect
import logging
import os
from typing import Callable, Any, List, Optional
from typing_extensions import Annotated

from fastapi import APIRouter, FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from prometheus_fastapi_instrumentator import Instrumentator
import pydantic
from fastapi.responses import Response, JSONResponse, StreamingResponse
import uvicorn

from leptonai.config import BASE_IMAGE, BASE_IMAGE_ARGS
from leptonai.photon.constants import METADATA_VCS_URL_KEY, LEPTON_DASHBOARD_URL
from leptonai.photon.download import fetch_code_from_vcs
from leptonai.util import switch_cwd
from .base import Photon, schema_registry

schemas = ["py"]


class PNGResponse(StreamingResponse):
    media_type = "image/png"


class WAVResponse(StreamingResponse):
    media_type = "audio/wav"


def create_model_for_func(func: Callable, func_name: Optional[str] = None):
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

    func_name = func_name or func.__name__
    request_model = pydantic.create_model(
        f"{func_name.capitalize()}Input",
        **params,
        **keyword_only_params,
        __config__=config,
    )

    return_type = inspect.signature(func).return_annotation

    if inspect.isclass(return_type) and issubclass(return_type, Response):
        response_model = None
        response_class = return_type
    else:
        if return_type is inspect.Signature.empty:
            return_type = Any

        class Config:
            arbitrary_types_allowed = True

        response_model = pydantic.create_model(
            f"{func_name.capitalize()}Output",
            input=request_model,
            output=(return_type, None),
            __config__=Config,
        )
        response_class = JSONResponse
    return request_model, response_model, response_class


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

    image: str = BASE_IMAGE
    args: list = BASE_IMAGE_ARGS
    requirement_dependency: Optional[List[str]] = None
    system_dependency: Optional[List[str]] = None
    vcs_url: Optional[str] = None

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
    def _infer_requirement_dependency():
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
            if pkg.startswith("pytest") or pkg == "parameterized" or pkg == "responses":
                # test related packages
                continue
            filtered_pkgs.append(pkg)
        return filtered_pkgs

    @property
    def _requirement_dependency(self):
        # If users have specified the requirement_dependency, use it and do not
        # try to infer
        if self.requirement_dependency is not None:
            return self.requirement_dependency

        try:
            requirement_dependency = self._infer_requirement_dependency()
        except Exception as e:
            logger.warning(f"Failed to get pip dependencies: {e}")
            requirement_dependency = []
        return requirement_dependency

    @property
    def metadata(self):
        res = super().metadata

        res["openapi_schema"] = self._create_app(load_mount=False).openapi()

        res["py_obj"] = {
            "name": self.__class__.__qualname__,
            "obj_pkl_file": self.obj_pkl_filename,
        }

        res.update({"requirement_dependency": self._requirement_dependency})
        res.update({"system_dependency": self.system_dependency})
        res.update({METADATA_VCS_URL_KEY: self.vcs_url})

        res.update(
            {
                "image": self.image,
                "args": self.args,
            }
        )

        return res

    @property
    def _extra_files(self):
        res = super()._extra_files
        res.update(
            {
                self.obj_pkl_filename: cloudpickle.dumps(self),
            }
        )
        return res

    @classmethod
    def load(cls, photon_file, metadata):
        obj_pkl_filename = metadata["py_obj"]["obj_pkl_file"]
        with photon_file.open(obj_pkl_filename) as obj_pkl_file:
            py_obj = cloudpickle.loads(obj_pkl_file.read())
        return py_obj

    def init(self):
        pass

    def call_init(self):
        if not self._init_called:
            self._init_called = True
            self._init_res = self.init()
        return self._init_res

    @abstractmethod
    def run(self, *args, **kwargs):
        raise NotImplementedError

    @staticmethod
    def _add_cors_middlewares(app):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                LEPTON_DASHBOARD_URL,
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _create_app(self, load_mount):
        title = self.name.replace(".", "_")
        app = FastAPI(title=title)

        # web hosted cdn and inference api have different domains:
        # https://github.com/leptonai/lepton/issues/358
        # TODO: remove this once our Ingress is capable of handling all these
        # and make all communication internal from the deployment point of view
        self._add_cors_middlewares(app)

        self._register_routes(app, load_mount)
        self._collect_metrics(app)
        return app

    @staticmethod
    def _uvicorn_log_config():
        # Filter out /healthz and /metrics from uvicorn access log
        class LogFilter(logging.Filter):
            def filter(self, record: logging.LogRecord) -> bool:
                return (
                    record.getMessage().find("/healthz ") == -1
                    and record.getMessage().find("/metrics ") == -1
                )

        logging.getLogger("uvicorn.access").addFilter(LogFilter())

        # prepend timestamp to log
        log_config = copy.deepcopy(uvicorn.config.LOGGING_CONFIG)
        for formatter, config in log_config["formatters"].items():
            config["fmt"] = "%(asctime)s - " + config["fmt"]
        return log_config

    def launch(self, host="0.0.0.0", port=8080, log_level="info"):
        self.call_init()
        app = self._create_app(load_mount=True)
        log_config = self._uvicorn_log_config()
        return uvicorn.run(
            app, host=host, port=port, log_level=log_level, log_config=log_config
        )

    @staticmethod
    def _collect_metrics(app):
        latency_lowr_buckets = tuple(
            # 0 ~ 1s: 10ms per bucket
            [ms / 1000 for ms in range(10, 1000, 10)]
            # 1 ~ 10s: 100ms per bucket
            + [ms / 1000 for ms in range(1000, 10 * 1000, 100)]
        )
        instrumentator = Instrumentator().instrument(
            app, latency_lowr_buckets=latency_lowr_buckets
        )

        @app.on_event("startup")
        async def _startup():
            instrumentator.expose(app, endpoint="/metrics")

    def _register_routes(self, app, load_mount):
        try:
            import gradio as gr
        except ImportError:
            has_gradio = False
        else:
            has_gradio = True

        api_router = APIRouter()
        for path, (func, kwargs) in self.routes.items():
            if kwargs.get("mount"):
                if not load_mount:
                    continue
                if not has_gradio:
                    logger.warning(f'Gradio is not installed. Skip mounting "{path}"')
                    continue

                num_params = len(inspect.signature(func).parameters)
                if num_params > 2:
                    raise ValueError(
                        "Gradio mount function should only have zero or one (app)"
                        " argument"
                    )
                if num_params == 2:
                    gr_blocks = func.__get__(self, self.__class__)(app)
                else:
                    gr_blocks = func.__get__(self, self.__class__)()
                if not isinstance(gr_blocks, gr.Blocks):
                    raise RuntimeError(
                        "Currently `mount` only supports Gradio Blocks. Got"
                        f" {type(gr_blocks)}"
                    )
                app = gr.mount_gradio_app(app, gr_blocks, f"/{path}")
                continue

            def create_typed_handler(func, kwargs):
                method = func.__get__(self, self.__class__)
                request_model, response_model, response_class = create_model_for_func(
                    method, func_name=path
                )
                if "example" in kwargs:
                    request_model = Annotated[
                        request_model, Body(example=kwargs["example"])
                    ]
                if "examples" in kwargs:
                    request_model = Annotated[
                        request_model, Body(examples=kwargs["examples"])
                    ]
                vd = pydantic.decorator.ValidatedFunction(method, None)

                async def typed_handler(request: request_model):
                    logger.info(request)
                    try:
                        res = vd.execute(request)
                    except Exception as e:
                        logger.error(e)
                        if isinstance(e, HTTPException):
                            return JSONResponse(
                                {"error": e.detail}, status_code=e.status_code
                            )
                        return JSONResponse({"error": str(e)}, status_code=500)
                    else:
                        if not isinstance(res, response_class):
                            res = response_class(res)
                        return res

                typed_handler_kwargs = {
                    "response_model": response_model,
                    "response_class": response_class,
                }
                return typed_handler, typed_handler_kwargs

            typed_handler, typed_handler_kwargs = create_typed_handler(func, kwargs)
            api_router.add_api_route(
                f"/{path}", typed_handler, methods=["POST"], **typed_handler_kwargs
            )
        app.include_router(api_router)

    @staticmethod
    def handler(path=None, **kwargs):
        def decorator(func):
            path_ = path if path is not None else func.__name__
            routes = get_routes(func)
            if path_ in routes:
                raise ValueError(f"Path {path_} already exists: {routes[path_]}")

            @functools.wraps(func)
            def wrapped_func(self, *args, **kwargs):
                self.call_init()
                return func(self, *args, **kwargs)

            routes[path_] = (func, kwargs)
            return wrapped_func

        return decorator

    @classmethod
    def create_from_model_str(cls, name, model_str):
        schema, s = model_str.split(":", maxsplit=1)
        if schema not in schemas:
            raise ValueError(f"Schema should be one of ({schemas}): but got {schema}")
        url_and_path, cls_name = s.rsplit(":", maxsplit=1)

        url_and_path_parts = url_and_path.rsplit(":", maxsplit=1)
        if len(url_and_path_parts) > 1:
            if len(url_and_path_parts) != 2:
                raise ValueError(f"Doesn't meet 'url:path' format: {url_and_path}")
            vcs_url, path = url_and_path_parts
            cwd = fetch_code_from_vcs(vcs_url)
        else:
            vcs_url = None
            path = url_and_path
            cwd = os.getcwd()

        with switch_cwd(cwd):
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
            if vcs_url is not None:
                runner.vcs_url = vcs_url
            return runner


handler = RunnerPhoton.handler


schema_registry.register(schemas, RunnerPhoton.create_from_model_str)
