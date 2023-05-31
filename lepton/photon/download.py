import os
import shutil

from loguru import logger

from lepton.config import CACHE_DIR


def fetch_code_from_vcs(url, target_dir=None):
    try:
        import pip
    except ImportError:
        raise RuntimeError("pip is not installed")

    try:
        from pip._internal.models.link import Link
        from pip._internal.utils.misc import hide_url
        from pip._internal.vcs import vcs
    except ImportError:
        raise RuntimeError(
            f"VCS functionality is not available in this version ({pip.__version__}) of pip, try upgrading pip via `pip install --upgrade pip`"
        )

    link = Link(url)
    hidden_url = hide_url(url)

    if not link.is_vcs:
        if not link.scheme:
            # default to use git+https protocol
            url = f"git+https://{url}"
        elif len(link.scheme.split("+")) == 1:
            # default to use git protocol
            url = f"git+{url}"
        link = Link(url)
        hidden_url = hide_url(url)

    if not link.is_vcs:
        raise ValueError(f"{hidden_url} is not a valid VCS url")

    vcs_backend = vcs.get_backend_for_scheme(link.scheme)
    if not vcs_backend:
        raise ValueError(f"Unrecognized VCS backend for {hidden_url}")

    if target_dir is None:
        target_dir = os.path.join(
            str(CACHE_DIR),
            link.netloc.lstrip("/"),
            link.path.lstrip("/").split("@")[0],
        )

    vcs_backend.obtain(url=hidden_url, dest=target_dir, verbosity=-1)

    if link.subdirectory_fragment:
        return os.path.join(target_dir, link.subdirectory_fragment)
    else:
        return target_dir
