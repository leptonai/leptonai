from abc import abstractmethod
import anyio
import asyncio
from collections import OrderedDict
import copy
import functools
import cloudpickle
import importlib
import importlib.util
import inspect
import logging
import os
import sys
import threading
import traceback
import types
from typing import Callable, Any, List, Dict, Optional, Set, Iterator, Type
from typing_extensions import Annotated
import uuid
import warnings
import zipfile

import click
from fastapi import APIRouter, FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.responses import (  # noqa: F401
    Response,
    JSONResponse,
    FileResponse,
    StreamingResponse,
)
from loguru import logger
from prometheus_fastapi_instrumentator import Instrumentator
import pydantic
import pydantic.decorator
import uvicorn
import uvicorn.config

from leptonai.config import (  # noqa: F401
    ALLOW_ORIGINS_URLS,
    BASE_IMAGE,
    BASE_IMAGE_ARGS,
    BASE_IMAGE_CMD,
    DEFAULT_PORT,
    ENV_VAR_REQUIRED,
    PYDANTIC_MAJOR_VERSION,
    VALID_SHAPES,
)
from leptonai.photon.constants import METADATA_VCS_URL_KEY
from leptonai.photon.download import fetch_code_from_vcs
from leptonai.photon.types import (  # noqa: F401
    FileParam,
    lepton_pickle,
    lepton_unpickle,
    is_pickled,
    LeptonPickled,
    PNGResponse,
    WAVResponse,
)
from leptonai.util import switch_cwd, patch, asyncfy_with_semaphore
from .base import BasePhoton, schema_registry
from .batcher import batch
from .background import BackgroundTask
from .rate_limit import RateLimiter
import leptonai._internal.logging as internal_logging

schemas = ["py"]


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

    if len(args) > 0:
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

                class config:  # type: ignore
                    extra = "allow"

            else:
                config = pydantic.ConfigDict(extra="allow")  # type: ignore
        else:
            config = None  # type: ignore

        func_name = func_name or func.__name__
        request_model = pydantic.create_model(
            f"{func_name.capitalize()}Input",
            **params,
            **keyword_only_params,
            __config__=config,  # type: ignore
        )
    else:
        request_model = None

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
            config = pydantic.ConfigDict(arbitrary_types_allowed=True)  # type: ignore

        response_model = pydantic.create_model(
            f"{func_name.capitalize()}Output",
            output=(return_type, None),
            __config__=config,  # type: ignore
        )
        response_class = JSONResponse
    return request_model, response_model, response_class


PHOTON_HANDLER_PARAMS_KEY = "__photon_handler_params__"


# A utility lock for the photons to use when running the _call_init_once function.
# The reason it is not inside the Photon class is that, the Photon class is going to be
# cloudpickled, and cloudpickle does not work with threading.Lock.
# A downside is that, if the user creates multiple photons in the same process, and they
# all call _call_init_once at the same time, they will be serialized by this lock. This is
# not a big deal, because the init function is usually not a bottleneck.
_photon_initialize_lock = threading.Lock()


class Photon(BasePhoton):
    photon_type: str = "photon"
    obj_pkl_filename: str = "obj.pkl"
    py_src_filename: str = "py.py"

    # Required python dependencies that you usually install with `pip install`. For example, if
    # your photon depends on `numpy`, you can set `requirement_dependency=["numpy"]`. If your
    # photon depends on a package installable over github, you can set the dependency to
    # `requirement_dependency=["git+xxxx"] where `xxxx` is the url to the github repo.
    #
    # Experimental feature: if you specify "uninstall xxxxx", instead of installing the library,
    # we will uninstall the library. This is useful if you want to uninstall a library that is
    # in conflict with some other libraries, and need to sequentialize a bunch of pip installs
    # and uninstalls. The exact correctness of this will really depend on pip and the specific
    # libraries you are installing and uninstalling, so please use this feature with caution.
    requirement_dependency: Optional[List[str]] = None

    # System dependencies that can be installed via `apt install`. FOr example, if your photon
    # depends on `ffmpeg`, you can set `system_dependency=["ffmpeg"]`.
    system_dependency: Optional[List[str]] = None

    # The deployment template that gives a (soft) reminder to the users about how to use the
    # photon. For example, if your photon has the following:
    #   - requires gpu.a10 to run
    #   - a required env variable called ENV_A, and the user needs to set the value.
    #   - an optional env variable called ENV_B with default value "DEFAULT_B"
    #   - a required secret called SECRET_A, and the user needs to choose the secret.
    # Then, the deployment template should look like:
    #     deployment_template: Dict = {
    #       "resource_shape": "gpu.a10",
    #       "env": {
    #         "ENV_A": ENV_VAR_REQUIRED,
    #         "ENV_B": "DEFAULT_B",
    #       },
    #       "secret": [
    #         "SECRET_A",
    #       ],
    #     }
    # During photon init time, we will check the existence of the env variables and secrets,
    # issue RuntimeError of the required ones are not set, and set default values for non-existing
    # env variables that have default values.
    deployment_template: Dict[str, Any] = {
        "resource_shape": None,
        "env": {},
        "secret": [],
    }

    # The maximum number of concurrent requests that the photon can handle. In default when the photon
    # concurrency is 1, all the endpoints defined by @Photon.handler is mutually exclusive, and at any
    # time only one endpoint is running. This does not include system generated endpoints such as
    # /openapi.json, /metrics, /healthz, /favicon.ico, etc.
    #
    # This parameter does not apply to any async endpoints you define. In other words, if you define
    # an endpoint like
    #   @Photon.handler
    #   async def foo(self):
    #       ...
    # then the endpoint is not subject to the photon concurrency limit. You will need to manually
    # limit the concurrency of the endpoint yourself.
    #
    # Note that, similar to the standard multithreading design pattens, the Photon class cannot guarantee
    # thread safety when handler_max_concurrency > 1. The lepton ai framework itself is thread safe, but the
    # thread safety of the methods defines in the Photon class needs to be manually guaranteed by the
    # author of the photon.
    handler_max_concurrency: int = 1
    background_tasks_max_concurrency: int = 1

    # The docker base image to use for the photon. In default, we encourage you to use the
    # default base image, which provides a blazing fast loading time when running photons
    # remotely. On top of the default image, you can then install any additional dependencies
    # via `requirement_dependency` or `system_dependency`.
    image: str = BASE_IMAGE

    # The args for the base image.
    args: List[str] = BASE_IMAGE_ARGS
    cmd: Optional[List[str]] = BASE_IMAGE_CMD
    exposed_port: int = DEFAULT_PORT

    # Port used for liveness check, use the same
    # port as the deployment server by default.
    health_check_liveness_tcp_port: Optional[int] = None

    # The git repository to check out as part of the photon deployment phase.
    vcs_url: Optional[str] = None

    def __init__(self, name=None, model=None):
        """
        Initializes a Photon.
        """
        if name is None:
            name = self.__class__.__qualname__
        if model is None:
            model = self.__class__.__qualname__
        super().__init__(name=name, model=model)
        self._init_called = False
        self._init_res = None

        # TODO(Yangqing): add sanity check to see if the user has set handler_max_concurrency too high to
        # be handled by the default anyio number of threads.
        self._handler_semaphore: anyio.Semaphore = anyio.Semaphore(
            self.handler_max_concurrency
        )

        self._background_tasks: Set[BackgroundTask] = set()
        self._background_task_semaphore: anyio.Semaphore = anyio.Semaphore(
            self.background_tasks_max_concurrency
        )

    def _on_background_task_done(self, task):
        """
        Internal function to remove the background task when it is done. You
        do not need to call this manually.
        """
        logger.debug(f"Background task {task.get_name()} is done and removed")
        self._background_tasks.remove(task)

    def add_background_task(self, func, *args, **kwargs):
        """
        Adds a background task to the background task queue. Note that to cope
        with most AI workloads, which are usually compute heavy and mutually exclusive
        on many resources (including e.g. the PyTorch runtime itself), we limit the
        number of concurrent background tasks to 1.

        Args:
            func: the Callable function to run. It should be a sync function to not
                block the main event loop. This function will be called in a separate
                thread.
            *args, **kwargs: the args and kwargs to pass to the function.
        """
        try:
            anyio.get_current_task()
            in_event_loop = True
        except RuntimeError:
            in_event_loop = False

        def _run_background_task():
            co = BackgroundTask(func, *args, **kwargs)
            task = asyncio.create_task(
                co(self._background_task_semaphore), name=uuid.uuid4()
            )
            self._background_tasks.add(task)
            logger.debug(f"Created background task {task.get_name()} in event loop")
            task.add_done_callback(self._on_background_task_done)

        if in_event_loop:
            _run_background_task()
        else:
            anyio.from_thread.run_sync(_run_background_task)

    @classmethod
    def _gather_routes(cls):
        def update_routes(old_, new_):
            for path, routes in new_.items():
                for method, route in routes.items():
                    old_.setdefault(path, {})[method] = route

        res = {}

        for base in cls._iter_ancestors():
            base_routes = {}
            for attr_name in dir(base):
                attr_val = getattr(base, attr_name)
                if hasattr(attr_val, PHOTON_HANDLER_PARAMS_KEY) and callable(attr_val):
                    path, method, func, kwargs = getattr(
                        attr_val, PHOTON_HANDLER_PARAMS_KEY
                    )
                    base_routes.setdefault(path, {})[method] = (func, kwargs)
            update_routes(res, base_routes)

        return res

    @classmethod
    def _iter_ancestors(cls) -> Iterator[Type["Photon"]]:
        yield cls
        for base in cls.__bases__:
            if base == Photon:
                # We still yield the Photon class, in case in the future, we add
                # default paths etc. in the Photon class.
                yield base
            elif not issubclass(base, Photon):
                # We do not yield non-Photon base classes, and any base class of
                # the Photon class (such as BasePhoton)
                continue
            else:
                yield from base._iter_ancestors()

    @property
    def _requirement_dependency(self) -> List[str]:
        deps = []
        # We add dependencies from ancestor classes to derived classes
        # and keep the order. Because we now support installation and uninstallation,
        # we do not remove redundant dependencies automatically.
        for base in reversed(list(self._iter_ancestors())):
            if base.requirement_dependency:
                deps.extend(base.requirement_dependency)
        # Do not sort or uniq pip deps lines, as order matters
        return deps

    @property
    def _system_dependency(self) -> List[str]:
        deps = OrderedDict()
        for base in reversed(list(self._iter_ancestors())):
            if base.system_dependency:
                deps.update({dep: None for dep in base.system_dependency})
        # NB: maybe we can sort and uniq system deps lines
        return list(deps.keys())

    @property
    def _deployment_template(self) -> Dict[str, Any]:
        # Verify and return the deployment template.
        if self.deployment_template is None:
            return {}
        # doing sanity check for the fields
        sanity_checked_fields = ["resource_shape", "env", "secret"]
        if any(
            field not in sanity_checked_fields
            for field in self.deployment_template.keys()
        ):
            raise ValueError(
                "Deployment template encountered a field that is not supported."
                f" Supported fields are: {sanity_checked_fields}."
            )
        # doing sanity check for the values
        resource_shape = self.deployment_template.get("resource_shape")
        if resource_shape is not None:
            if not isinstance(resource_shape, str):
                raise ValueError(
                    "Deployment template resource_shape must be a string. Found"
                    f" {resource_shape} instead."
                )
            if resource_shape not in VALID_SHAPES:
                # For now, only issue a warning if the user specified a non-standard
                # shape, and not an error. This is because we want to allow future versions
                # of the CLI to support more shapes, and we do not want to break the
                # compatibility.
                warnings.warn(
                    "Deployment template resource_shape"
                    f" {resource_shape} is not one of the"
                    " standard shapes. Just a kind reminder."
                )
        env = self.deployment_template.get("env", {})
        if not isinstance(env, dict):
            raise ValueError(
                f"Deployment template envs must be a dict. Found {env} instead."
            )
        for key, value in env.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError(
                    "Deployment template envs keys/values must be strings. Found"
                    f" {key}:{value} instead."
                )
        secret = self.deployment_template.get("secret", [])
        if not isinstance(secret, list):
            raise ValueError(
                f"Deployment template secrets must be a list. Found {secret} instead."
            )
        if any(not isinstance(s, str) for s in secret):
            raise ValueError(
                "Deployment template secrets must be a list of strings. Found"
                f" {secret} instead."
            )
        return self.deployment_template

    @property
    def metadata(self):
        res = super().metadata

        res["openapi_schema"] = self._create_app(load_mount=False).openapi()

        res["py_obj"] = {
            "name": self.__class__.__qualname__,
            "obj_pkl_file": self.obj_pkl_filename,
            "py_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        }

        try:
            src_file = inspect.getfile(self.__class__)
        except Exception as e:
            res["py_obj"]["src_file"] = None
            res["py_obj"]["src_file_error"] = str(e)
        else:
            res["py_obj"]["src_file"] = src_file

        res.update({"requirement_dependency": self._requirement_dependency})
        res.update({"system_dependency": self._system_dependency})
        res.update({METADATA_VCS_URL_KEY: self.vcs_url})

        res.update({"deployment_template": self._deployment_template})

        res.update({
            "image": self.image,
            "args": self.args,
            "exposed_port": self.exposed_port,
        })

        if self.health_check_liveness_tcp_port is not None:
            res["health_check_liveness_tcp_port"] = self.health_check_liveness_tcp_port

        if self.cmd is not None:
            res["cmd"] = self.cmd

        return res

    def save(self, path: Optional[str] = None):
        path = super().save(path=path)
        with zipfile.ZipFile(path, "a") as photon_file:
            with photon_file.open(self.obj_pkl_filename, "w") as obj_pkl_file:
                pickler = cloudpickle.CloudPickler(obj_pkl_file, protocol=4)

                def pickler_dump(obj):
                    # internal logger opens keeps the log file opened
                    # in append mode, which is not supported to
                    # pickle, so needs to close it first before
                    # pickling
                    internal_logging.disable()
                    pickler.dump(obj)
                    internal_logging.enable()

                try:
                    from cloudpickle.cloudpickle import _extract_code_globals

                    orig_function_getnewargs = pickler._function_getnewargs
                except (ImportError, AttributeError):
                    pickler_dump(self)
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
                            pickler_dump(self)

            src_str = None
            try:
                src_file = inspect.getfile(self.__class__)
            except Exception:
                pass
            else:
                if os.path.exists(src_file):
                    with open(src_file, "rb") as src_file_in:
                        src_str = src_file_in.read()
            if src_str is None:
                try:
                    src_str = inspect.getsource(self.__class__)
                except Exception:
                    pass
            else:
                with photon_file.open(self.py_src_filename, "w") as src_file_out:
                    src_file_out.write(src_str)
        return path

    @classmethod
    def load(cls, photon_file, metadata) -> "Photon":
        py_version = metadata["py_obj"].get("py_version")
        cur_py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        if py_version is not None and py_version != cur_py_version:
            logger.warning(
                f"Photon was created with Python {py_version} but now run with Python"
                f" {cur_py_version}, which may cause unexpected behavior."
            )
        obj_pkl_filename = metadata["py_obj"]["obj_pkl_file"]
        with photon_file.open(obj_pkl_filename) as obj_pkl_file:
            py_obj = cloudpickle.loads(obj_pkl_file.read())
        return py_obj

    def init(self):
        """
        The explicit init function that your derived Photon class should implement.
        This function is called when we create a deployment from a photon, and is
        guaranteed to run before the first api call served by the photon.
        """
        # The Photon init function sets the envs and secrets specified in the deployment template
        envs = self._deployment_template.get("env", {})
        for key in envs:
            if os.environ.get(key) is None:
                if envs[key] == ENV_VAR_REQUIRED:
                    raise RuntimeError(
                        f"This photon expects env variable {key} but it s not set."
                    )
                else:
                    os.environ[key] = envs[key]
        secrets = self._deployment_template.get("secret", [])
        for s in secrets:
            if os.environ.get(s) is None:
                raise RuntimeError(f"This photon expects secret {s} but it s not set.")

    def _call_init_once(self):
        """
        Internal function that calls the init function once.
        """
        if not self._init_called:
            with _photon_initialize_lock:
                # acquire the lock, and check again.
                if self._init_called:
                    return
                else:
                    # run Photon's init function.
                    Photon.init(self)
                    # run the user-defined init function
                    self._init_res = self.init()
                    self._init_called = True
        return self._init_res

    @abstractmethod
    def run(self, *args, **kwargs):
        raise NotImplementedError

    @staticmethod
    def _add_cors_middlewares(app):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=ALLOW_ORIGINS_URLS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _create_app(self, load_mount):
        title = self._photon_name.replace(".", "_")
        app = FastAPI(
            title=title,
            description=(
                self.__doc__
                if self.__doc__
                else f"Lepton AI Photon API {self._photon_name}"
            ),
        )

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
        logger.info(
            "\n".join([
                "\nIf you are using standard photon, a few urls that may be helpful:",
                "\t- "
                + click.style(f"http://{host}:{port}/docs", fg="green", bold=True)
                + " OpenAPI documentation",
                "\t- "
                + click.style(f"http://{host}:{port}/redoc", fg="green", bold=True)
                + " Redoc documentation",
                "\t- "
                + click.style(
                    f"http://{host}:{port}/openapi.json", fg="green", bold=True
                )
                + " Raw OpenAPI schema",
                "\t- "
                + click.style(f"http://{host}:{port}/metrics", fg="green", bold=True)
                + " Prometheus metrics",
                "\nIf you are using python clients, here is an example code snippet:",
                "\tfrom leptonai.client import Client, local",
                f"\tclient = Client(local(port={port}))",
                "\tclient.healthz()  # checks the health of the photon",
                "\tclient.paths()  # lists all the paths of the photon",
                (
                    "\tclient.method_name?  # If client has a method_name method,"
                    " get the docstring"
                ),
                "\tclient.method_name(...)  # calls the method_name method",
                (
                    "If you are using ipython, you can use tab completion by typing"
                    " `client.` and then press tab.\n"
                ),
            ])
        )

    def _uvicorn_run(self, host, port, log_level, log_config):
        app = self._create_app(load_mount=True)

        # /healthz added at this point will be at the end of `app.routes`,
        # so it will act as a fallback
        @app.get("/healthz", include_in_schema=False)
        def healthz():
            return {"status": "ok"}

        if (
            self.health_check_liveness_tcp_port is None
            or self.health_check_liveness_tcp_port == port
        ):

            @app.get("/livez", include_in_schema=False)
            def livez():
                return {"status": "ok"}

        # /favicon.ico added at this point will be at the end of `app.routes`,
        # so it will act as a fallback
        @app.get("/favicon.ico", include_in_schema=False)
        def favicon():
            path = os.path.join(os.path.dirname(__file__), "favicon.ico")
            if not os.path.exists(path):
                return Response(status_code=404)
            return FileResponse(path)

        config = uvicorn.Config(app, host=host, port=port, log_config=log_config)
        lepton_uvicorn_server = uvicorn.Server(config=config)
        self._print_launch_info(host, port, log_level)
        lepton_uvicorn_server.run()

    def _run_liveness_server(self):
        def run_server():
            app = FastAPI()

            @app.get("/livez")
            def livez():
                return {"status": "ok"}

            port = self.health_check_liveness_tcp_port
            logger.info(f"Launching liveness server on port {port}")
            uvicorn.run(app, host="localhost", port=port, log_level="error")

        threading.Thread(target=run_server, daemon=True).start()

    def launch(
        self,
        host: Optional[str] = "0.0.0.0",
        port: Optional[int] = DEFAULT_PORT,
        log_level: Optional[str] = "info",
    ):
        """
        Launches the api service for the photon.
        """
        if (
            self.health_check_liveness_tcp_port is not None
            and self.health_check_liveness_tcp_port != port
        ):
            self._run_liveness_server()

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

        try:
            import gradio as gr  # type: ignore

            has_gradio = True
        except ImportError:
            has_gradio = False

        try:
            from flask import Flask  # type: ignore

            has_flask = True
        except ImportError:
            has_flask = False

        if isinstance(subapp, FastAPI):
            app.include_router(subapp.router, prefix=f"/{path}")
        elif isinstance(subapp, StaticFiles):
            app.mount(f"/{path}", subapp)
        elif isinstance(subapp, Photon):
            subapp_real_app = subapp._create_app(load_mount=True)
            app.include_router(subapp_real_app.router, prefix=f"/{path}")
        elif subapp.__module__ == "asgi_proxy" and subapp.__name__ == "asgi_proxy":
            # asgi_proxy returns a lambda function (`<function
            # asgi_proxy.asgi_proxy.<locals>.asgi_proxy(scope,
            # receive, send)>`), it's not easy to type check it, so we
            # just do name checking here
            app.mount(f"/{path}", subapp)
        elif not has_gradio and not has_flask:
            logger.warning(
                f"Skip mounting {path} as none of [`gradio`, `flask`] is"
                " installed and it is not a FastAPI"
            )
        elif has_gradio and isinstance(subapp, gr.Blocks):  # type: ignore
            gr.mount_gradio_app(app, subapp, f"/{path}")  # type: ignore
        elif has_flask and isinstance(subapp, Flask):  # type: ignore
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
            method, func_name=self.__class__.__name__ + "_" + path
        )

        if http_method.lower() == "post" and request_model is not None:
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
                kwargs["max_batch_size"],
                kwargs["max_wait_time"],
                self._handler_semaphore,
            )(method)
        else:
            method = asyncfy_with_semaphore(method, self._handler_semaphore)

        if kwargs.get("rate_limit") is not None:
            rate_limiter = RateLimiter(kwargs["rate_limit"])

            def check_rate_limit():
                if not rate_limiter.hit():
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded, please try again later.",
                    )

        else:
            rate_limiter = None

        if http_method.lower() == "post":
            # In the post mode, we do the following:
            # - If the handler specifies "use_raw_args", then we don't wrap the args to a
            # json body, but instead just pass the raw args up to fastapi.
            # - Otherwise, we wrap the args to a json body, and use the request_model
            # as the pydantic model to validate the json body.
            # - If no args are specified, we don't wrap anything.
            if kwargs.get("use_raw_args"):

                @functools.wraps(
                    method,
                    assigned=(
                        wa
                        for wa in functools.WRAPPER_ASSIGNMENTS
                        if wa != "__annotations__"
                    ),  # type: ignore
                )
                async def wrapped_method(*args, **kwargs):
                    if rate_limiter is not None:
                        check_rate_limit()
                    try:
                        res = await method(*args, **kwargs)
                    except Exception as e:
                        logger.error(traceback.format_exc())
                        if isinstance(e, HTTPException):
                            return JSONResponse(
                                {"error": e.detail}, status_code=e.status_code
                            )
                        return JSONResponse({"error": str(e)}, status_code=500)
                    else:
                        if not isinstance(res, response_class):
                            res = response_class(res)
                        return res

                typed_handler = types.FunctionType(
                    wrapped_method.__code__,
                    globals(),
                    "typed_handler",
                    wrapped_method.__defaults__,
                    wrapped_method.__closure__,
                )  # type: ignore
                # Transfer the defaults and signature from the original method.
                typed_handler.__annotations__ = method.__annotations__
                typed_handler.__defaults__ = method.__defaults__  # type: ignore
                typed_handler.__doc__ = method.__doc__
                typed_handler.__kwdefaults__ = method.__kwdefaults__  # type: ignore
                typed_handler.__signature__ = inspect.signature(method)  # type: ignore
            elif request_model is not None:
                vd = pydantic.decorator.validate_arguments(method).vd

                # for post handler, we change endpoint function's signature to make
                # it taking json body as input, so do not copy the
                # `__annotations__` attribute here
                @functools.wraps(
                    method,
                    assigned=(
                        wa
                        for wa in functools.WRAPPER_ASSIGNMENTS
                        if wa != "__annotations__"
                    ),  # type: ignore
                )
                async def typed_handler(request: request_model):  # type: ignore
                    if rate_limiter is not None:
                        check_rate_limit()

                    try:
                        res = await vd.execute(request)
                    except Exception as e:
                        logger.error(traceback.format_exc())
                        if isinstance(e, HTTPException):
                            return JSONResponse(
                                {"error": e.detail}, status_code=e.status_code
                            )
                        return JSONResponse({"error": str(e)}, status_code=500)
                    else:
                        if not isinstance(res, response_class):
                            res = response_class(res)
                        return res

                delattr(typed_handler, "__wrapped__")
            else:
                # for post handler, we change endpoint function's signature to make
                # it taking json body as input, so do not copy the
                # `__annotations__` attribute here
                @functools.wraps(
                    method,
                    assigned=(
                        wa
                        for wa in functools.WRAPPER_ASSIGNMENTS
                        if wa != "__annotations__"
                    ),  # type: ignore
                )
                async def typed_handler():  # type: ignore
                    if rate_limiter is not None:
                        check_rate_limit()
                    try:
                        res = await method()
                    except Exception as e:
                        logger.error(traceback.format_exc())
                        if isinstance(e, HTTPException):
                            return JSONResponse(
                                {"error": e.detail}, status_code=e.status_code
                            )
                        return JSONResponse({"error": str(e)}, status_code=500)
                    else:
                        if not isinstance(res, response_class):
                            res = response_class(res)
                        return res

                delattr(typed_handler, "__wrapped__")

        elif http_method.lower() == "get":

            @functools.wraps(method)
            async def typed_handler(*args, **kwargs):
                if rate_limiter is not None:
                    check_rate_limit()

                try:
                    res = await method(*args, **kwargs)
                except Exception as e:
                    logger.error(traceback.format_exc())
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
        for path, routes in self._gather_routes().items():
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

            @functools.wraps(func)
            def wrapped_func(self, *args, **kwargs):
                self._call_init_once()
                return func(self, *args, **kwargs)

            setattr(
                wrapped_func, PHOTON_HANDLER_PARAMS_KEY, (path_, method, func, kwargs)
            )
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
            if os.path.exists(path):
                path_parts = os.path.splitext(os.path.basename(path))
                if len(path_parts) != 2 or path_parts[1] != ".py":
                    raise ValueError(f"File path should be a Python file (.py): {path}")
                module_name = path_parts[0]
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None:
                    raise ValueError(
                        f"Could not import Python module from path: {path}"
                    )
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                if spec.loader is None:
                    raise ValueError(
                        f"Could not import Python module from path: {path}"
                    )
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
            elif "." in path:
                module_str, _, cls_name = path.rpartition(".")
                try:
                    module = importlib.import_module(module_str)
                except ModuleNotFoundError:
                    raise ValueError(
                        f"'{path}' is neither an existing file nor an importable python"
                        " variable"
                    )
            else:
                raise ValueError(
                    f"'{path}' is neither an existing file nor an importable python"
                    " variable"
                )

            cloudpickle.register_pickle_by_value(module)
            ph_cls = getattr(module, cls_name)
            if not inspect.isclass(ph_cls) or not issubclass(ph_cls, cls):
                raise ValueError(f"{cls_name} is not a sub class of {cls.__name__}")
            ph = ph_cls(name=name, model=model_str)
            if vcs_url is not None:
                ph.vcs_url = vcs_url
            return ph


handler = Photon.handler


schema_registry.register(schemas, Photon.create_from_model_str)
