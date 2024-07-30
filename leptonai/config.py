"""
Overall configurations and constants for the Lepton AI python library.
"""

import os
from pathlib import Path
import sys
import warnings

import pydantic
import pydantic.version
from typing import Generic, TypeVar

# Cache directory for Lepton's local configurations.
# Usually, you should not need to change this. In cases like unit testing, you
# can change this to a directory that is available via the environment variable
# `LEPTON_CACHE_DIR`, BEFORE IMPORTING LEPTONAI.
#
# Implementation note: cache directory is not always created, and this is by design.
# In some cases such as function compute, you may not have a directory to write
# cache into. As a result, we create the cache directory when we need to write to it.
CACHE_DIR = Path(os.environ.get("LEPTON_CACHE_DIR", Path.home() / ".cache" / "lepton"))

################################################################################
# Configurations you can change to customize Lepton's behavior.
################################################################################

# Whether to trust remote code. This is often used in model repositories such as
# HuggingFace's tokenizer. In default, we will allow users to trust remote code
# and run such tokenizers. Set the environment variable `LEPTON_TRUST_REMOTE_CODE`
# to `false` to disable this behavior.
TRUST_REMOTE_CODE = os.environ.get("LEPTON_TRUST_REMOTE_CODE", "true").lower() in (
    "true",
    "1",
    "t",
    "on",
)

# Whether to set deployments to have a default timeout of 1 hour. This is often
# preferred in a development environment. Set the environment variable `LEPTON_DEFAULT_TIMEOUT`
# to `false` to disable this behavior.
_DEFAULT_TIMEOUT_IF_NOT_SPECIFIED = 3600
if os.environ.get(
    "LEPTON_DEFAULT_TIMEOUT", str(_DEFAULT_TIMEOUT_IF_NOT_SPECIFIED)
).lower() in ("f", "off", "false", "0"):
    # Do not set a default timeout.
    DEFAULT_TIMEOUT = None
else:
    timeout_str = os.environ.get(
        "LEPTON_DEFAULT_TIMEOUT", str(_DEFAULT_TIMEOUT_IF_NOT_SPECIFIED)
    )
    try:
        DEFAULT_TIMEOUT = int(timeout_str)
    except ValueError:
        DEFAULT_TIMEOUT = 3600
        print(
            f"You have set an invalid value for LEPTON_DEFAULT_TIMEOUT {timeout_str}."
            f" Using default value of {DEFAULT_TIMEOUT} seconds."
        )


# In cloudrun, the default timeout is also set to 1 hour. However, even if we set
# LEPTON_DEFAULT_TIMEOUT to false, we still want to set the default timeout inside
# cloudrun, because it was expected to be in-process.
try:
    CLOUDRUN_DEFAULT_TIMEOUT = int(
        os.environ.get("LEPTON_CLOUDRUN_DEFAULT_TIMEOUT", "3600")
    )
except ValueError:
    CLOUDRUN_DEFAULT_TIMEOUT = 3600  # 1 hour
    print(
        "You have set an invalid value for LEPTON_CLOUDRUN_DEFAULT_TIMEOUT"
        f" {os.environ.get('LEPTON_CLOUDRUN_DEFAULT_TIMEOUT')}. Using default value"
        f" of {CLOUDRUN_DEFAULT_TIMEOUT} seconds."
    )


################################################################################
# Automatically generated constants. You do not need to change these.
################################################################################
T = TypeVar("T")

# Implementation of three compatible classes / functions for pydantic 1.x and 2.x:
# 1. compatible_field_validator: A dummy wrapper that is backward compatible with
# pydantic 1.x. However, this validator only supports very simple field validators
# where no fancy features other than the field name is used. If you need to use more
# advanced features, either manually write two separate functions, or use
# v2only_field_validator.
# 2. v2only_field_validator: A dummy wrapper that is only compatible with pydantic
# 2.x. This validator is intended to be used when you need to use advanced features
# in pydantic 2.x, and you can safely ignore the coverage drop in pydantic 1.x.
# 3. CompatibleRootModel: A simple RootModel that is compatible with both pydantic
# 1.x and 2.x. It only supports one field, which is root, and simple functionalities
# such as dict and json. Note that this class is not fully compatible with pydantic
# 2.x, and it is only intended to be used in simple cases.
if pydantic.version.VERSION < "2.0.0":
    PYDANTIC_MAJOR_VERSION = 1
    import json
    from pydantic.class_validators import validator as compatible_field_validator

    warnings.warn(
        "You are using pydantic 1.x, which is not fully supported by Lepton AI. We"
        " strongly recommend you to upgrade to pydantic 2.x if possible.",
        DeprecationWarning,
    )

    def v2only_field_validator(*args, **kwargs):
        """
        A dummy wrapper that is backward compatible with pydantic 1.x. However, this
        validator will actually do no validation in pydantic 1.x - meaning that coverage
        will be worse. We recommend users to upgrade to pydantic 2.x if possible.
        """

        def decorator(f):
            return f

        return decorator

    class CompatibleRootModel(pydantic.BaseModel, Generic[T]):  # type: ignore
        """
        CompatibleRootModel backports a simple RootModel from pydantic 2.x to pydantic 1.x.
        It only supports one field, which is root, and simple functionalities such as dict and
        json. Note that this class is not fully compatible with pydantic 2.x, and it is only
        intended to be used in simple cases.
        """

        root: T

        class Config:
            orm_mode = True

        def dict(self, *args, **kwargs):
            return self.root

        def json(self, *args, **kwargs):
            return json.dumps(self.root, separators=(",", ":"))

        @classmethod
        def parse_obj(cls, obj):
            return cls(root=obj)

        @classmethod
        def parse_raw(cls, *args, **kwargs):
            obj = super().parse_raw(*args, **kwargs)
            return cls(root=obj)

        @classmethod
        def parse_file(cls, *args, **kwargs):
            obj = super().parse_file(*args, **kwargs)
            return cls(root=obj)

else:
    PYDANTIC_MAJOR_VERSION = 2
    from pydantic import field_validator, ValidationInfo, RootModel  # type: ignore # noqa: F401

    compatible_field_validator = field_validator  # type: ignore
    v2only_field_validator = field_validator  # type: ignore

    class CompatibleRootModel(RootModel[T], Generic[T]):
        """
        CompatibleRootModel backports a simple RootModel from pydantic 2.x to pydantic 1.x.
        It only supports one field, which is root, and simple functionalities such as dict and
        json. Note that this class is not fully compatible with pydantic 2.x, and it is only
        intended to be used in simple cases.
        """

        pass


################################################################################
# Lepton internals. Do not change these as they will change the behavior of the
# library and APIs.
################################################################################

# Cache directory for Lepton's local storage: database, logs, etc.
# To change the cache directory, set the environment variable LEPTON_CACHE_DIR before importing leptonai.
# User note: cache directory is not directly created, and this is by design - in some cases such as
# function compute, you may not have a directory to write cache into. As a result, we create the cache
# directory when we need to write to it.
#
# If you are in need of accessing the cache directory, use the functions `create_cached_dir_if_needed()`
# in `leptonai.utils`.
CACHE_DIR = Path(os.environ.get("LEPTON_CACHE_DIR", Path.home() / ".cache" / "lepton"))
DB_PATH = CACHE_DIR / "lepton.db"
LOGS_DIR = CACHE_DIR / "logs"


def _to_bool(s: str) -> bool:
    """
    Convert a string to a boolean value.
    """
    if not isinstance(s, str):
        raise TypeError(f"Expected a string, got {type(s)}")
    true_values = ("yes", "true", "t", "1", "y", "on", "aye", "yea")
    false_values = ("no", "false", "f", "0", "n", "off", "nay", "")
    s = s.lower()
    if s in true_values:
        return True
    elif s in false_values:
        return False
    else:
        raise ValueError(
            f"Invalid boolean value: {s}. Valid true values: {true_values}. Valid false"
            f" values: {false_values}."
        )


def _is_rocm() -> bool:
    """
    Detects if we are using rocm.

    If the user specified LEPTON_BASE_IMAGE_FORCE_ROCM to any true values, then
    _is_rocm() returns True. If it is not specified, we rely on cuda to see if
    we are building rocm. This function is only intended to be used to determine
    the base image type, and you should directly use torch.version.hip in your
    user code.
    """
    return _to_bool(os.environ.get("LEPTON_BASE_IMAGE_FORCE_ROCM", "false"))


# Lepton's base image and image repository location.
BASE_IMAGE_VERSION = "0.21.4"
BASE_IMAGE_REGISTRY = "default"
BASE_IMAGE_REPO = f"{BASE_IMAGE_REGISTRY}/lepton"
BASE_IMAGE = f"{BASE_IMAGE_REPO}:photon{'-rocm' if _is_rocm() else ''}-py{sys.version_info.major}.{sys.version_info.minor}-runner-{BASE_IMAGE_VERSION}"  # noqa: E501
BASE_IMAGE_ARGS = ["--shm-size=1g"]

# By default, platform runs lep ph run -f ${photon_file_path}
BASE_IMAGE_CMD = None

# Default shape used by the Lepton deployments.
if os.environ.get("LEPTON_DEFAULT_RESOURCE_SHAPE"):
    DEFAULT_RESOURCE_SHAPE = os.environ["LEPTON_DEFAULT_RESOURCE_SHAPE"]
else:
    DEFAULT_RESOURCE_SHAPE = "cpu.small"

# Default port used by the Lepton deployments.
DEFAULT_PORT = 8080

try:
    DEFAULT_TIMEOUT_KEEP_ALIVE = int(
        os.environ.get("LEPTON_TIMEOUT_KEEP_ALIVE", "1800")
    )
except ValueError:
    DEFAULT_TIMEOUT_KEEP_ALIVE = 1800  # 30 minutes
    print(
        "You have set an invalid value for LEPTON_TIMEOUT_KEEP_ALIVE."
        f" Using default value of {DEFAULT_TIMEOUT_KEEP_ALIVE} seconds."
    )

# When the server is shut down, we will wait for all the ongoing requests to finish before
# shutting down. This is the timeout for the graceful shutdown. If the timeout is
# reached, we will force kill the server. If not set, this is the default that we will use.
# Implementation note: None means we will use the default behavior of asyncio.
DEFAULT_TIMEOUT_GRACEFUL_SHUTDOWN = (
    int(os.environ["LEPTON_TIMEOUT_GRACEFUL_SHUTDOWN"])
    if os.environ.get("LEPTON_TIMEOUT_GRACEFUL_SHUTDOWN")
    else None
)

# For some advanced users as well as debugging use, the users might hard-code a different
# pydantic and cloudpickle version in the created photons. This environment variable is used
# to force photon's prepare() function to install the pydantic and cloudrun version specified
# in the photon. Note that this leads to untested compatibility issues - since cloudpickle and
# pydantic are known in not being forward or backward compatible. Use at your own risk.
FORCE_PIP_INSTALL_PYDANTIC_AND_CLOUDPICKLE = _to_bool(
    os.environ.get("LEPTON_FORCE_PIP_INSTALL_PYDANTIC_AND_CLOUDPICKLE", "false")
)

# During some deployment environments, the server might run behind a load balancer, and during
# the shutdown time, the load balancer will send a SIGTERM to uvicorn to shut down the server.
# The default behavior of uvicorn is to immediately stop receiving new traffic, and it is problematic
# when the load balancer need to wait for some time to propagate the TERMINATING status to
# other components of the distributed system. This parameter controls the grace period before
# uvicorn rejects incoming traffic on SIGTERM.
if os.environ.get("LEPTON_INCOMING_TRAFFIC_GRACE_PERIOD"):
    # If the user has explicitly set the grace period, we will use the user's setting.
    DEFAULT_INCOMING_TRAFFIC_GRACE_PERIOD = int(
        os.environ["LEPTON_INCOMING_TRAFFIC_GRACE_PERIOD"]
    )
elif "LEPTON_WORKSPACE_ID" in os.environ and "LEPTON_DEPLOYMENT_NAME" in os.environ:
    # Else, if we are running on the Lepton platform, we will use the default grace period
    # that we tested on the platform for maximum smoothness in alleviating the distributed
    # envoy update.
    DEFAULT_INCOMING_TRAFFIC_GRACE_PERIOD = 300
else:
    DEFAULT_INCOMING_TRAFFIC_GRACE_PERIOD = 5


_LOCAL_DEPLOYMENT_TOKEN = None


def set_local_deployment_token(token: str):
    """
    Sets the local token used by Lepton deployments. If the token is empty, we will not
    set the token in the deployment. If the token is set, all local endpoints defined
    by Photon.handler are protected by the token.

    Note that on the Lepton platform, the token is managed by the platform, so we
    will ignore the local deployment token.
    """
    if token is None:
        raise RuntimeError(
            'Token cannot be None. To set an empty token, use empty string ("").'
        )
    if "LEPTON_WORKSPACE_ID" in os.environ and "LEPTON_DEPLOYMENT_NAME" in os.environ:
        warnings.warn(
            "We are running on the Lepton platform, so we will ignore the local"
            " deployment token."
        )
    else:
        global _LOCAL_DEPLOYMENT_TOKEN
        _LOCAL_DEPLOYMENT_TOKEN = token


def get_local_deployment_token() -> str:
    """
    Gets the local deployment token. If the token is explicitly set by set_local_deployment_token,
    return the token. Otherwise, return the token from the environment variable LEPTON_LOCAL_DEPLOYMENT_TOKEN.
    If the environment variable is not set, return an empty string.
    """
    if _LOCAL_DEPLOYMENT_TOKEN is None:
        return os.environ.get("LEPTON_LOCAL_DEPLOYMENT_TOKEN", "")
    else:
        return _LOCAL_DEPLOYMENT_TOKEN


# In the photon's deployment template, this means you will need to specify env variables.
ENV_VAR_REQUIRED = "PLEASE_ENTER_YOUR_ENV_VARIABLE_HERE_(LEPTON_ENV_VAR_REQUIRED)"

# Valid resource shapes
VALID_SHAPES = [
    "cpu.small",
    "cpu.medium",
    "cpu.large",
    "gpu.t4",
    "gpu.a10",
    "gpu.a10.6xlarge",
    "gpu.a100-40gb",
    "gpu.2xa100-40gb",
    "gpu.4xa100-40gb",
    "gpu.8xa100-40gb",
    "gpu.a100-80gb",
    "gpu.2xa100-80gb",
    "gpu.4xa100-80gb",
    "gpu.8xa100-80gb",
    "gpu.h100-pcie",
    "gpu.h100-sxm",
    "gpu.2xh100-sxm",
    "gpu.4xh100-sxm",
    "gpu.8xh100-sxm",
]

# Current API path to resolve a workspace url. When we calls the URL with a json
# body {"id": <workspace_id>}, it returns the workspace url.
WORKSPACE_URL_RESOLVER_API = "https://portal.lepton.ai/api/workspace"

# Current workspace api path
WORKSPACE_API_PATH = "/api/v1"

# Lepton reserved secret and env prefix. One is not supposed to use this in `--env` or `--secret` flags.
LEPTON_RESERVED_ENV_NAMES = {
    "LEPTON_WORKSPACE_ID",
    "LEPTON_DEPLOYMENT_NAME",
    "LEPTON_PHOTON_NAME",
    "LEPTON_PHOTON_ID",
    "LEPTON_RESOURCE_ACCELERATOR_TYPE",
}

if "LEPTON_ALLOW_ORIGINS" in os.environ:
    ALLOW_ORIGINS = os.environ["LEPTON_ALLOW_ORIGINS"].split(",")
else:
    ALLOW_ORIGINS = ["*"]

LEPTON_DASHBOARD_URL = "https://dashboard.lepton.ai"
# LEPTON_WORKSPACE_URL is used to get the web url for the workspace. Append "/dashboard" for the workspace dashboard.
LEPTON_WORKSPACE_URL = LEPTON_DASHBOARD_URL + "/workspace/{workspace_id}"
# LEPTON_DEPLOYMENT_URL is used to get the web url for the deployment.
# Append "/demo", "/api", "/metrics", "/events", "/replicas/list" for the deployment dashboard functions.
LEPTON_DEPLOYMENT_URL = LEPTON_WORKSPACE_URL + "/deployments/detail/{deployment_name}"
