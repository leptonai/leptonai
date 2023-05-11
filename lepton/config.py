import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CACHE_DIR = Path(os.environ.get("LEPTON_CACHE_DIR", Path.home() / ".cache" / "lepton"))
if not CACHE_DIR.exists():
    CACHE_DIR.mkdir(parents=True)

DB_PATH = CACHE_DIR / "lepton.db"

IMAGE_REPO = "605454121064.dkr.ecr.us-east-1.amazonaws.com"
