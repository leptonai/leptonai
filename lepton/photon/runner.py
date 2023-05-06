from abc import ABC, abstractmethod
import functools
import cloudpickle
from io import BytesIO
import inspect
from typing import Callable, Any

from fastapi import FastAPI, Request, APIRouter
from loguru import logger
import pydantic
from fastapi.responses import JSONResponse, Response, StreamingResponse
import uvicorn

from .base import Photon


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
    cls_src_filename: str = "cls.py"

    def __init__(self, name=None, model=None):
        if name is None:
            name = self.__class__.__qualname__
        if model is None:
            model = self.__class__.__qualname__
        super().__init__(name=name, model=model)
        self.routes = get_routes(self.__class__)
        self.init()

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
            "cls_src_file": self.cls_src_filename,
        }
        return res

    @property
    def extra_files(self):
        res = super().extra_files
        res.update(
            {
                self.obj_pkl_filename: cloudpickle.dumps(self),
                self.cls_src_filename: inspect.getsource(self.__class__),
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

    @abstractmethod
    def run(self, *args, **kwargs):
        raise NotImplementedError

    def launch(self, host="0.0.0.0", port=8080, log_level="info"):
        self.init()

        title = self.name.replace(".", "_")
        app = FastAPI(title=title)
        self._register_routes(app)
        return uvicorn.run(app, host=host, port=port, log_level=log_level)

    def _register_routes(self, app):
        api_router = APIRouter()
        for path, (func, response_class) in self.routes.items():
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

            routes[path_] = (func, response_class)
            return func

        return decorator


handler = RunnerPhoton.handler
