from lepton.db import DB
from .api import create, load, save  # noqa: F401
from .hf import HuggingfacePhoton  # noqa: F401

DB.execute(
    "CREATE TABLE IF NOT EXISTS photon (id INTEGER PRIMARY KEY, name TEXT, model TEXT, path TEXT)"
)
