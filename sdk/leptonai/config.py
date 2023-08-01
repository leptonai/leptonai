"""
Overall configurations and constants for the Lepton SDK.
"""
import os
from pathlib import Path
import sys

from dotenv import load_dotenv
import pydantic.version

load_dotenv()

# Cache directory for Lepton's local databases etc.
CACHE_DIR = Path(os.environ.get("LEPTON_CACHE_DIR", Path.home() / ".cache" / "lepton"))
if not CACHE_DIR.exists():
    CACHE_DIR.mkdir(parents=True)
DB_PATH = CACHE_DIR / "lepton.db"

# Lepton's base image and image repository location.
BASE_IMAGE_VERSION = "0.1.12"
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
# Dashboard URL
LEPTON_DASHBOARD_URL = "https://dashboard.lepton.ai"

if pydantic.version.VERSION < "2.0.0":
    PYDANTIC_MAJOR_VERSION = 1
else:
    PYDANTIC_MAJOR_VERSION = 2
