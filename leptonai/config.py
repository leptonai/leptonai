"""
Overall configurations and constants for the Lepton AI python library.
"""

import os
from pathlib import Path
import sys

import pydantic.version

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
CLOUDRUN_DEFAULT_TIMEOUT = 3600
if os.environ.get("LEPTON_CLOUDRUN_DEFAULT_TIMEOUT", None) is not None:
    try:
        CLOUDRUN_DEFAULT_TIMEOUT = int(
            os.environ.get("LEPTON_CLOUDRUN_DEFAULT_TIMEOUT")
        )
    except ValueError:
        print(
            "You have set an invalid value for LEPTON_CLOUDRUN_DEFAULT_TIMEOUT"
            f" {os.environ.get('LEPTON_CLOUDRUN_DEFAULT_TIMEOUT')}. Using default value"
            f" of {CLOUDRUN_DEFAULT_TIMEOUT} seconds."
        )


################################################################################
# Automatically generated constants. You do not need to change these.
################################################################################

if pydantic.version.VERSION < "2.0.0":
    PYDANTIC_MAJOR_VERSION = 1
else:
    PYDANTIC_MAJOR_VERSION = 2


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
# If you are in need of accessing the cache directory, use the functions `create_cached_dir_if_needed()` in `leptonai.utils`.
CACHE_DIR = Path(os.environ.get("LEPTON_CACHE_DIR", Path.home() / ".cache" / "lepton"))
DB_PATH = CACHE_DIR / "lepton.db"
LOGS_DIR = CACHE_DIR / "logs"

# Lepton's base image and image repository location.
BASE_IMAGE_VERSION = "0.11.1"
BASE_IMAGE_REGISTRY = "default"
BASE_IMAGE_REPO = f"{BASE_IMAGE_REGISTRY}/lepton"
BASE_IMAGE = f"{BASE_IMAGE_REPO}:photon-py{sys.version_info.major}.{sys.version_info.minor}-runner-{BASE_IMAGE_VERSION}"
BASE_IMAGE_ARGS = ["--shm-size=1g"]

# Default port used by the Lepton deployments.
DEFAULT_PORT = 8080

# Current API path to resolve a workspace url. When we calls the URL with a json
# body {"id": <workspace_id>}, it returns the workspace url.
WORKSPACE_URL_RESOLVER_API = "https://portal.lepton.ai/api/workspace"

# Current workspace api path
WORKSPACE_API_PATH = "/api/v1"

# Lepton reserved secret and env prefix. One is not supposed to use this in `--env` or `--secret` flags.
LEPTON_RESERVED_ENV_PREFIX = "lepton_"
# Homepage URL
LEPTON_HOMEPAGE_URL = "https://lepton.ai"
LEPTON_HOMEPAGE_WWW_URL = "https://www.lepton.ai"
# Dashboard URL
LEPTON_DASHBOARD_URL = "https://dashboard.lepton.ai"
LEPTON_DASHBOARD_DAILY_URL = "https://dashboard.daily.lepton.ai"

ALLOW_ORIGINS_URLS = [
    LEPTON_HOMEPAGE_URL,
    LEPTON_HOMEPAGE_WWW_URL,
    LEPTON_DASHBOARD_URL,
    LEPTON_DASHBOARD_DAILY_URL,
]

# LEPTON_WORKSPACE_URL is used to get the web url for the workspace. Append "/dashboard" for the workspace dashboard.
LEPTON_WORKSPACE_URL = LEPTON_DASHBOARD_URL + "/workspace/{workspace_id}"
# LEPTON_DEPLOYMENT_URL is used to get the web url for the deployment.
# Append "/demo", "/api", "/metrics", "/events", "/replicas/list" for the deployment dashboard functions.
LEPTON_DEPLOYMENT_URL = LEPTON_WORKSPACE_URL + "/deployments/detail/{deployment_name}"
