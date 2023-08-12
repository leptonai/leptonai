import os

from loguru import logger

from leptonai.config import CACHE_DIR


def fetch_code_from_vcs(url, target_dir=None):
    try:
        import pip
    except ImportError:
        raise RuntimeError("pip is not installed")

    try:
        from pip._internal.models.link import Link
        from pip._internal.utils.misc import (
            hide_url,
            split_auth_netloc_from_url,
            parse_netloc,
        )
        from pip._internal.vcs import vcs  # type: ignore
    except ImportError:
        raise RuntimeError(
            f"VCS functionality is not available in this version ({pip.__version__}) of"
            " pip, try upgrading pip via `pip install --upgrade pip`"
        )

    url = os.path.expandvars(url)
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

    _, netloc, (auth_user, auth_passwd) = split_auth_netloc_from_url(url)
    # TODO: check if git@github.com format url works with user:token
    if link.scheme in ("git+http", "git+https") and netloc.startswith("github.com"):
        autofilled_user = False
        if auth_user is None and os.environ.get("GITHUB_USER"):
            auth_user = os.environ.get("GITHUB_USER")
            autofilled_user = True
        autofilled_passwd = False
        if auth_passwd is None and os.environ.get("GITHUB_TOKEN"):
            auth_passwd = os.environ.get("GITHUB_TOKEN")
            autofilled_passwd = True
        # TODO: handle the case that only one of user and passwd is resolved
        if (autofilled_user or autofilled_passwd) and (auth_user and auth_passwd):
            url = url.replace(netloc, f"{auth_user}:{auth_passwd}@{netloc}")
            link = Link(url)
            hidden_url = hide_url(url)
            logger.info(
                "Using environment variables GITHUB_USER and GITHUB_TOKEN to auth with"
                f" github.com: {hidden_url}"
            )
            _, netloc, (_, _) = split_auth_netloc_from_url(url)

    if target_dir is None:
        path_parts = [str(CACHE_DIR)]
        if netloc:
            hostname, _ = parse_netloc(netloc)
            path_parts.append(hostname.lstrip("/"))
        path_parts.append(link.path.lstrip("/").split("@")[0])
        target_dir = os.path.join(*path_parts)

    vcs_backend.obtain(url=hidden_url, dest=target_dir, verbosity=-1)

    if link.subdirectory_fragment:
        return os.path.join(target_dir, link.subdirectory_fragment)
    else:
        return target_dir
