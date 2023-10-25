import anyio
from contextlib import contextmanager, closing
from functools import wraps, partial
import inspect
import os
import socket
from typing import Optional
import re
from urllib.parse import urlparse

from rich.console import Console

from leptonai import config

console = Console(highlight=False)


def create_cached_dir_if_needed():
    """
    Creates the local cached dir if it doesn't exist.
    """
    if not config.CACHE_DIR.exists():
        config.CACHE_DIR.mkdir(parents=True)


@contextmanager
def switch_cwd(path):
    old_cwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(old_cwd)


def check_photon_name(name):
    assert isinstance(name, str), "Photon name must be a string"

    if len(name) > 32:
        raise ValueError(
            f"Invalid Photon name '{name}': Name must be less than 32 characters"
        )

    # copied from
    # https://github.com/leptonai/lepton/blob/732311f395476b67295a730b0be4d104ed7f5bef/api-server/util/util.go#L26
    name_regex = r"^[a-z]([-a-z0-9]*[a-z0-9])?$"
    if not re.match(name_regex, name):
        raise ValueError(
            f"Invalid Photon name '{name}': Name must consist of lower case"
            " alphanumeric characters or '-', and must start with an alphabetical"
            " character and end with an alphanumeric character"
        )


@contextmanager
def patch(obj, attr, val):
    old_val = getattr(obj, attr)
    try:
        setattr(obj, attr, val)
        yield
    finally:
        setattr(obj, attr, old_val)


def asyncfy(func):
    """Decorator that makes a function async. Note that this does not actually make
    the function asynchroniously running in a separate thread, it just wraps it in
    an async function. If you want to actually run the function in a separate thread,
    consider using asyncfy_with_semaphore.

    Args:
        func (function): Function to make async
    """

    if inspect.iscoroutinefunction(func):
        return func

    @wraps(func)
    async def async_func(*args, **kwargs):
        return func(*args, **kwargs)

    return async_func


def asyncfy_with_semaphore(func, semaphore: Optional[anyio.Semaphore]):
    """Decorator that makes a function async, as well as running in a separate thread,
    with the concurrency controlled by the semaphore. If the function is already async,
    this decorator is ignored. If Semaphore is None, we do not enforce an upper bound
    on the number of concurrent calls (but it is still bound by the number of threads
    that anyio defines as an upper bound).

    Args:
        func (function): Function to make async
        semaphore (anyio.Semaphore or None): Semaphore to use for concurrency control. If func
            is already async, this argument is ignored. If func is sync, it will be
            guarded by the semaphore.
    """

    if inspect.iscoroutinefunction(func):
        return func

    @wraps(func)
    async def async_func(*args, **kwargs):
        if semaphore is None:
            return await anyio.to_thread.run_sync(partial(func, *args, **kwargs))
        else:
            async with semaphore:
                return await anyio.to_thread.run_sync(partial(func, *args, **kwargs))

    return async_func


def _is_valid_url(candidate_str: str) -> bool:
    parsed = urlparse(candidate_str)
    return parsed.scheme != "" and parsed.netloc != ""


def _is_local_url(candidate_str: str) -> bool:
    parsed = urlparse(candidate_str)
    local_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
    return parsed.hostname in local_hosts


def find_available_port(port=None):
    if port is None:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(("", 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]

    def is_port_occupied(port):
        """
        Returns True if the port is occupied, False otherwise.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", port)) == 0

    while is_port_occupied(port):
        console.print(
            f"Port [yellow]{port}[/] already in use. Incrementing port number to"
            " find an available one."
        )
        port += 1
    return port
