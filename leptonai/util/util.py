from typing import Any
from urllib.parse import urlparse

from leptonai import config


def create_cached_dir_if_needed():
    """
    Creates the local cached dir if it doesn't exist.
    """
    if not config.CACHE_DIR.exists():
        # add exist_ok because if this is invoked by multiple threads/processes
        # (e.g. concurrent cli runs), the path may be created by another
        # thread/process between the exists() check and the mkdir() call.
        config.CACHE_DIR.mkdir(parents=True, exist_ok=True)


def is_valid_url(candidate_str: Any) -> bool:
    if not isinstance(candidate_str, str):
        return False
    parsed = urlparse(candidate_str)
    return parsed.scheme != "" and parsed.netloc != ""
