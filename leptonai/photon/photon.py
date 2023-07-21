from abc import abstractmethod
import base64
import copy
import functools
import cloudpickle
from io import BytesIO
import importlib
import inspect
import logging
import os
import re
import sys
from typing import Callable, Any, List, Optional
from typing_extensions import Annotated
import warnings
import zipfile

import click
from fastapi import APIRouter, FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from loguru import logger
from prometheus_fastapi_instrumentator import Instrumentator
import pydantic
import pydantic.decorator
from pydantic import BaseModel, validator
from fastapi.responses import Response, JSONResponse, StreamingResponse
import uvicorn

from leptonai.config import (
    BASE_IMAGE,
    BASE_IMAGE_ARGS,
    DEFAULT_PORT,
    PYDANTIC_MAJOR_VERSION,
)
from leptonai.photon.constants import METADATA_VCS_URL_KEY, LEPTON_DASHBOARD_URL
from leptonai.photon.download import fetch_code_from_vcs
from leptonai.util import switch_cwd, patch, asyncfy
from .base import BasePhoton, schema_registry
from .batcher import batch

schemas = ["py"]


_BASE64FILE_ENCODED_PREFIX = "encoded:"


class FileParam(BaseModel):
    content: bytes

    # allow creating FileParam with position args
    def __init__(self, content: bytes):
        super().__init__(content=content)

    def __str__(self):
        return f"FileParam(id={id(self)}) {len(self.content)} Bytes"

    def __repr__(self):
        return str(self)

    # TODO: cached property?
    @property
    def file(self):
        return BytesIO(self.content)

    @validator("content", pre=True)
    def validate_content(cls, content):
        # when users create a FileParam, content is a file-like object
        if hasattr(content, "read"):
            return content.read()
        elif isinstance(content, bytes):
            return content
        elif isinstance(content, str):
            # when the FileParam is created from a request, content is a base64 encoded string
            if content.startswith(_BASE64FILE_ENCODED_PREFIX):
                return base64.b64decode(
                    content[len(_BASE64FILE_ENCODED_PREFIX) :].encode("utf-8")
                )
            else:
                return content.encode("utf-8")
        else:
            raise ValueError(
                "content must be a file-like object or bytes or a base64 encoded"
                f" string: {content}"
            )

    @staticmethod
    def encode(content: bytes) -> str:
        return _BASE64FILE_ENCODED_PREFIX + base64.b64encode(content).decode("utf-8")

    if PYDANTIC_MAJOR_VERSION <= 1:

        class Config:
            json_encoders = {bytes: lambda v: FileParam.encode(v)}

    else:
        from pydantic import field_serializer

        @field_serializer("content")
        def _encode_content(self, content: bytes, _) -> str:
            return self.encode(content)


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
    if len(args) > 0 and (args[0] == "self" or args[0] == "cls"):
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
        if PYDANTIC_MAJOR_VERSION <= 1:

            class config:
                extra = "allow"

        else:
            config = pydantic.ConfigDict(extra="allow")
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

        if PYDANTIC_MAJOR_VERSION <= 1:

            class config:
                arbitrary_types_allowed = True

        else:
            config = pydantic.ConfigDict(arbitrary_types_allowed=True)

        response_model = pydantic.create_model(
            f"{func_name.capitalize()}Output",
            output=(return_type, None),
            __config__=config,
        )
        response_class = JSONResponse
    return request_model, response_model, response_class


_routes = {}


def get_routes(var):
    qualname = var.__qualname__
    if not inspect.isclass(var):
        qualname = ".".join(qualname.split(".")[:-1])

    mod_path = None

    if mod_path is None:
        try:
            mod = sys.modules[var.__module__]
            mod_path = os.path.abspath(mod.__file__)
        except (KeyError, AttributeError):
            pass
    if mod_path is None:
        try:
            mod_path = os.path.abspath(inspect.getfile(var))
        except (TypeError, OSError):
            # TypeError happens when var is not supported by inspect (like a built-in callable).
            # OSError happens when a Photon class is defined in an interactive session and not in a source file.
            # For these two cases, we cannot get the module path, so we just route back to the next available
            # option.
            pass
    if mod_path is None:
        mod_path = var.__module__

    cls_name = f"{mod_path}:{qualname}"
    if cls_name not in _routes:
        _routes[cls_name] = {}
    return _routes[cls_name]


class Photon(BasePhoton):
    photon_type: str = "photon"
    obj_pkl_filename: str = "obj.pkl"

    image: str = BASE_IMAGE
    """
    The docker base image to use for the photon. In default, we encourage you to use the
    default base image, which provides a blazing fast loading time when running photons
    remotely. On top of the default image, you can then install any additional dependencies
    via `requirement_dependency` or `system_dependency`.
    """

    args: list = BASE_IMAGE_ARGS
    """
    The args for the base image.
    """

    requirement_dependency: Optional[List[str]] = None
    """
    Required python dependencies that you usually install with `pip install`. For example, if
    your photon depends on `numpy`, you can set `requirement_dependency=["numpy"]`. If your
    photon depends on a package installable over github, you can set the dependency to
    `requirement_dependency=["git+xxxx"] where `xxxx` is the url to the github repo.
    """

    capture_requirement_dependency: bool = False
    """
    Experimental feature: whether to automatically capture dependencies automaticlaly from the
    local environment. This is not recommended, as in many cases, we observe that local dependencies
    may be polluted by different installation approaches (e.g. pip vs conda), and may result in
    unexpected behavior when running remotely. If you do want to use this feature, please make sure
    that you have a clean environment with only the dependencies you want to capture. We encourage
    you to use `requirement_dependency` instead.
    """

    system_dependency: Optional[List[str]] = None
    vcs_url: Optional[str] = None

    def __init__(self, name=None, model=None):
        if name is None:
            name = self.__class__.__qualname__
        if model is None:
            model = self.__class__.__qualname__
        super().__init__(name=name, model=model)
        self._routes = self._gather_routes()
        self._init_called = False
        self._init_res = None

    @classmethod
    def _gather_routes(cls):
        def update_routes(old_, new_):
            for path, routes in new_.items():
                for method, route in routes.items():
                    old_.setdefault(path, {})[method] = route

        res = {}

        for base in cls.__bases__:
            if base == BasePhoton:
                # BasePhoton should not have any routes
                continue
            update_routes(res, get_routes(base))

        update_routes(res, get_routes(cls))
        return res

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
            if pkg.startswith("-e") or re.search(r"@\s*file://", pkg):
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
            if self.capture_requirement_dependency:
                raise ValueError(
                    "Should not set `capture_requirement_dependency` to True when"
                    f" `requirement_dependency` is set ({self.requirement_dependency})"
                )
            return self.requirement_dependency

        if not self.capture_requirement_dependency:
            return []

        logger.info(
            "Auto capturing pip dependencies (note this could result in a large list of"
            " dependencies)"
        )
        try:
            requirement_dependency = self._infer_requirement_dependency()
        except Exception as e:
            logger.warning(f"Failed to auto capture pip dependencies: {e}")
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

        res.update(
            {"capture_requirement_dependency": self.capture_requirement_dependency}
        )
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

    def save(self, path: Optional[str] = None):
        path = super().save(path=path)
        with zipfile.ZipFile(path, "a") as photon_file:
            with photon_file.open(self.obj_pkl_filename, "w") as obj_pkl_file:
                pickler = cloudpickle.CloudPickler(obj_pkl_file, protocol=4)
                try:
                    from cloudpickle.cloudpickle import _extract_code_globals

                    orig_function_getnewargs = pickler._function_getnewargs
                except (ImportError, AttributeError):
                    pickler.dump(self)
                else:

                    def _function_getnewargs(func):
                        try:
                            g_names = _extract_code_globals(func.__code__)
                            for name in ["__file__", "__path__"]:
                                if name in g_names:
                                    warnings.warn(
                                        f"function {func} has used global variable"
                                        f" '{name}', its value"
                                        f" '{func.__globals__[name]}' is resolved"
                                        " during Photon creation instead of Deployment"
                                        " runtime, which may cause unexpected"
                                        " behavior."
                                    )
                        except Exception:
                            pass
                        return orig_function_getnewargs(func)

                    # We normally use loguru to do logging, in order
                    # to verify the warning message is working
                    # properly, we use assertWarns in unittest, which
                    # requires the warning message to be emiited by
                    # the python warnings module. So we need to patch
                    # the warning module to emit the warning message
                    # by warnings module but printed by loguru
                    showwarning_ = warnings.showwarning

                    def showwarning(message, *args, **kwargs):
                        logger.warning(message)
                        showwarning_(message, *args, **kwargs)

                    with patch(warnings, "showwarning", showwarning):
                        with patch(
                            pickler, "_function_getnewargs", _function_getnewargs
                        ):
                            pickler.dump(self)
        return path

    @classmethod
    def load(cls, photon_file, metadata):
        obj_pkl_filename = metadata["py_obj"]["obj_pkl_file"]
        with photon_file.open(obj_pkl_filename) as obj_pkl_file:
            py_obj = cloudpickle.loads(obj_pkl_file.read())
        return py_obj

    def init(self):
        pass

    def _call_init_once(self):
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

    @staticmethod
    def _print_launch_info(host, port, log_level):
        logger = logging.getLogger("Lepton Photon Launcher")
        logger.setLevel(log_level.upper())

        if not logger.hasHandlers():
            formatter = logging.Formatter(
                "%(asctime)s - \x1b[32m%(levelname)s\x1b[0m:  %(message)s\t"
            )
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.propagate = False
        # Send the welcome message, especially to make sure that users will know
        # whicl URL to visit in order to not get a "not found" error.
        logger.info("If you are using standard photon, a few urls that may be helpful:")
        logger.info(
            "\t- "
            + click.style(f"http://{host}:{port}/docs", fg="green", bold=True)
            + " OpenAPI documentation"
        )
        logger.info(
            "\t- "
            + click.style(f"http://{host}:{port}/redoc", fg="green", bold=True)
            + " Redoc documentation"
        )
        logger.info(
            "\t- "
            + click.style(f"http://{host}:{port}/openapi.json", fg="green", bold=True)
            + " Raw OpenAPI schema"
        )
        logger.info(
            "\t- "
            + click.style(f"http://{host}:{port}/metrics", fg="green", bold=True)
            + " Prometheus metrics"
        )

    def _uvicorn_run(self, host, port, log_level, log_config):
        def run_server():
            app = self._create_app(load_mount=True)

            @app.post("/lepton-restart", include_in_schema=False)
            def lepton_restart_handler():
                global lepton_uvicorn_restart
                global lepton_uvicorn_server

                lepton_uvicorn_restart = True
                # to hint uvicorn server to shutdown
                lepton_uvicorn_server.should_exit = True

            # make sure restart handler takes precedence over other
            # handlers (e.g. apps mounted at root path)
            app.routes.insert(0, app.routes.pop())

            # /healthz added at this point will be at the end of `app.routes`,
            # so it will act as a fallback
            @app.get("/healthz", include_in_schema=False)
            def healthz():
                return {"status": "ok"}

            global lepton_uvicorn_restart
            global lepton_uvicorn_server

            lepton_uvicorn_restart = False
            config = uvicorn.Config(app, host=host, port=port, log_config=log_config)
            lepton_uvicorn_server = uvicorn.Server(config=config)
            self._print_launch_info(host, port, log_level)
            lepton_uvicorn_server.run()

        while True:
            run_server()
            if lepton_uvicorn_restart:
                logger.info(f"Restarting server on {host}:{port}")
            else:
                break

    def launch(self, host="0.0.0.0", port=DEFAULT_PORT, log_level="info"):
        self._call_init_once()
        log_config = self._uvicorn_log_config()
        self._uvicorn_run(
            host=host, port=port, log_level=log_level, log_config=log_config
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
            instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)

    # helper function of _register_routes
    def _mount_route(self, app, path, func):
        num_params = len(inspect.signature(func).parameters)
        if num_params > 2:
            raise ValueError(
                "Mount function should only have zero or one (app) argument"
            )
        try:
            if num_params == 2:
                subapp = func.__get__(self, self.__class__)(app)
            else:
                subapp = func.__get__(self, self.__class__)()
        except ImportError as e:
            if "gradio" in str(e):
                logger.warning(f"Skip mounting {path} as `gradio` is not installed")
                return
            if "flask" in str(e):
                logger.warning(f"Skip mounting {path} as `flask` is not installed")
                return
            raise

        if isinstance(subapp, FastAPI):
            app.mount(f"/{path}", subapp)
            return

        try:
            import gradio as gr
        except ImportError:
            has_gradio = False
        else:
            has_gradio = True

        try:
            from flask import Flask
        except ImportError:
            has_flask = False
        else:
            has_flask = True

        if not has_gradio and not has_flask:
            logger.warning(
                f"Skip mounting {path} as none of [`gradio`, `flask`] is"
                " installed and it is not a FastAPI"
            )
            return

        if has_gradio and isinstance(subapp, gr.Blocks):
            gr.mount_gradio_app(app, subapp, f"/{path}")
        elif has_flask and isinstance(subapp, Flask):
            app.mount(f"/{path}", WSGIMiddleware(subapp))
        else:
            raise ValueError(
                f"Cannot mount {subapp} to {path} as it is not a FastAPI,"
                " gradio.Blocks or Flask"
            )
        return

    def _create_typed_handler(self, path, http_method, func, kwargs):
        method = func.__get__(self, self.__class__)

        request_model, response_model, response_class = create_model_for_func(
            method, func_name=path
        )

        if http_method.lower() == "post":
            if "example" in kwargs:
                request_model = Annotated[
                    request_model, Body(example=kwargs["example"])
                ]
            if "examples" in kwargs:
                request_model = Annotated[
                    request_model, Body(examples=kwargs["examples"])
                ]

        if kwargs.get("max_batch_size") is not None:
            method = batch(
                max_batch_size=kwargs["max_batch_size"],
                max_wait_time=kwargs["max_wait_time"],
            )(method)
        else:
            method = asyncfy(method)

        if http_method.lower() == "post":
            vd = pydantic.decorator.validate_arguments(method).vd

            async def typed_handler(request: request_model):
                logger.info(request)
                try:
                    res = await vd.execute(request)
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

        elif http_method.lower() == "get":

            @functools.wraps(method)
            async def typed_handler(*args, **kwargs):
                logger.info(f"args: {args}, kwargs: {kwargs}")
                try:
                    res = await method(*args, **kwargs)
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

        else:
            raise ValueError(f"Unsupported http method {http_method}")

        typed_handler_kwargs = {
            "response_model": response_model,
            "response_class": response_class,
        }
        return typed_handler, typed_handler_kwargs

    # helper function of _register_routes
    def _add_route(self, api_router, path, method, func, kwargs):
        typed_handler, typed_handler_kwargs = self._create_typed_handler(
            path, method, func, kwargs
        )
        api_router.add_api_route(
            f"/{path}",
            typed_handler,
            name=path,
            methods=[method],
            **typed_handler_kwargs,
        )

    def _register_routes(self, app, load_mount):
        api_router = APIRouter()
        for path, routes in self._routes.items():
            for method, (func, kwargs) in routes.items():
                if kwargs.get("mount"):
                    if load_mount:
                        self._mount_route(app, path, func)
                else:
                    self._add_route(api_router, path, method, func, kwargs)
        app.include_router(api_router)

    @staticmethod
    def _santity_check_handler_kwargs(kwargs):
        mbs, mwt = kwargs.get("max_batch_size"), kwargs.get("max_wait_time")
        if (mbs is None) != (mwt is None):
            raise ValueError(
                "max_batch_size and max_wait_time should be both specified or not, got"
                f" max_batch_size={mbs}, max_wait_time={mwt}"
            )

        if kwargs.get("mount") and (mbs is not None):
            raise ValueError("mount and batching cannot be used together")
        return

    @staticmethod
    def handler(path=None, method="POST", **kwargs):
        Photon._santity_check_handler_kwargs(kwargs)

        def decorator(func):
            path_ = path if path is not None else func.__name__
            path_ = path_.strip("/")
            routes = get_routes(func)
            if path_ in routes and method in routes[path_]:
                raise ValueError(
                    f"Handler (path={path_}, method={method}) already exists:"
                    f" {routes[path_][method]}"
                )

            @functools.wraps(func)
            def wrapped_func(self, *args, **kwargs):
                self._call_init_once()
                return func(self, *args, **kwargs)

            routes.setdefault(path_, {})[method] = (func, kwargs)
            return wrapped_func

        if callable(path) and not kwargs:
            # the decorator has been used without parenthesis, `path` is a
            # function here
            func_ = path
            path = func_.__name__
            return decorator(func_)
        else:
            return decorator

    @classmethod
    def _find_photon_subcls_names(cls, module):
        valid_cls_names = []
        for name, obj in inspect.getmembers(module):
            if obj is cls:
                continue
            if inspect.isclass(obj) and issubclass(obj, cls):
                valid_cls_names.append(name)
        return valid_cls_names

    @classmethod
    def create_from_model_str(cls, name, model_str):
        schema, s = model_str.split(":", maxsplit=1)
        if schema not in schemas:
            raise ValueError(f"Schema should be one of ({schemas}): but got {schema}")

        if ":" in s:
            url_and_path, cls_name = s.rsplit(":", maxsplit=1)
            if not cls_name.isidentifier():
                url_and_path, cls_name = s, None
        else:
            url_and_path, cls_name = s, None

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
            sys.modules[module_name] = module
            cloudpickle.register_pickle_by_value(module)
            if spec.loader is None:
                raise ValueError(f"Could not import Python module from path: {path}")
            spec.loader.exec_module(module)

            if cls_name is None:
                valid_cls_names = cls._find_photon_subcls_names(module)
                if len(valid_cls_names) == 0:
                    raise ValueError(
                        f"Can not find any sub classes of {cls.__name__} in {path}"
                    )
                elif len(valid_cls_names) > 1:
                    raise ValueError(
                        f"Found multiple sub classes of {cls.__name__} in {path}:"
                        f" {valid_cls_names}"
                    )
                else:
                    cls_name = valid_cls_names[0]
                    model_str = f"{model_str}:{cls_name}"

            ph_cls = getattr(module, cls_name)
            if not inspect.isclass(ph_cls) or not issubclass(ph_cls, cls):
                raise ValueError(f"{cls_name} is not a sub class of {cls.__name__}")
            ph = ph_cls(name=name, model=model_str)
            if vcs_url is not None:
                ph.vcs_url = vcs_url
            return ph


handler = Photon.handler


schema_registry.register(schemas, Photon.create_from_model_str)
