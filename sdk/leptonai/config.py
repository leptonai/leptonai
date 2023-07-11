import os
from pathlib import Path
import sys

from dotenv import load_dotenv
import pydantic.version

load_dotenv()

CACHE_DIR = Path(os.environ.get("LEPTON_CACHE_DIR", Path.home() / ".cache" / "lepton"))
if not CACHE_DIR.exists():
    CACHE_DIR.mkdir(parents=True)

DB_PATH = CACHE_DIR / "lepton.db"

BASE_IMAGE_VERSION = "0.1.7"
BASE_IMAGE = f"605454121064.dkr.ecr.us-east-1.amazonaws.com/lepton:photon-py{sys.version_info.major}.{sys.version_info.minor}-runner-{BASE_IMAGE_VERSION}"
BASE_IMAGE_ARGS = ["--shm-size=1g"]

WORKSPACE_URL_TEMPLATE = "https://{workspace_name}.cloud.lepton.ai"
WORKSPACE_API_PATH = "/api/v1"


if pydantic.version.VERSION < "2.0.0":
    PYDANTIC_MAJOR_VERSION = 1
else:
    PYDANTIC_MAJOR_VERSION = 2
