from contextlib import contextmanager
from functools import wraps
import inspect
import os
import re

from rich.console import Console

from leptonai.config import WORKSPACE_URL_TEMPLATE, WORKSPACE_API_PATH

console = Console(highlight=False)


def get_full_workspace_url(workspace_name):
    """
    Get the full URL for a workspace.
    """
    return WORKSPACE_URL_TEMPLATE.format(workspace_name=workspace_name)


def get_full_workspace_api_url(workspace_name):
    """
    Get the full URL for the API of a workspace.
    """
    return get_full_workspace_url(workspace_name) + WORKSPACE_API_PATH


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
    # https://github.com/leptonai/lepton/blob/732311f395476b67295a730b0be4d104ed7f5bef/lepton-api-server/util/util.go#L26
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
    """Decorator that makes a function async

    Args:
        func (function): Function to make async
    """

    if inspect.iscoroutinefunction(func):
        return func

    @wraps(func)
    async def async_func(*args, **kwargs):
        return func(*args, **kwargs)

    return async_func
