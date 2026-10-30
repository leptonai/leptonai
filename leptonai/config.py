"""
Overall configurations and constants for the Lepton AI python library.
"""

import os
from pathlib import Path
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

VERSION_CHECK_FILE: Path = CACHE_DIR / "latest_version_check"
VERSION_CHECK_INTERVAL_SEC: int = 60 * 60 * 24  # 24h

################################################################################
# Configurations you can change to customize Lepton's behavior.
################################################################################

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


# Default base image for batch jobs.
JOB_BASE_IMAGE = "nvcr.io/nvidia/pytorch:25.08-py3"

# Default shape used by the Lepton deployments.
if os.environ.get("LEPTON_DEFAULT_RESOURCE_SHAPE"):
    DEFAULT_RESOURCE_SHAPE = os.environ["LEPTON_DEFAULT_RESOURCE_SHAPE"]
else:
    DEFAULT_RESOURCE_SHAPE = "cpu.small"

# Valid resource shapes
VALID_SHAPES = [
    "cpu.small",
    "cpu.medium",
    "cpu.large",
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
    "gpu.h100-sxm",
    "gpu.2xh100-sxm",
    "gpu.4xh100-sxm",
    "gpu.8xh100-sxm",
]

DGXC_WORKSPACE_API_PATH = "/api/v2/workspaces/"

API_URL_BASE = "https://gateway.dgxc-lepton.nvidia.com"

DGXC_WORKSPACE_URL_RESOLVER_API = (
    "https://gateway.dgxc-lepton.nvidia.com/api/v2/workspaces"
)


# Current workspace api path
# Lepton reserved secret and env prefix. One is not supposed to use this in `--env` or `--secret` flags.
LEPTON_RESERVED_ENV_NAMES = {
    "LEPTON_WORKSPACE_ID",
    "LEPTON_DEPLOYMENT_NAME",
    "LEPTON_JOB_NAME",
    "LEPTON_RESOURCE_ACCELERATOR_TYPE",
    "LEPTON_WORKSPACE_ORIGIN_URL",
}

# Note: LEPTON_DEPLOYMENT_URL is temporarily removed to reduce workspace URL dependency
# This may be restored in the future if we implement a more flexible URL handling mechanism

# Dashboard URL related environment variables/configs are deprecated and removed.

SSH_PORT = 2222
TCP_PORT = 18888
TCP_JUPYTER_PORT = 18889
