from contextlib import contextmanager
import json
import os
import re
from rich.console import Console
from typing import Dict


console = Console(highlight=False)


def create_header(auth_token: str) -> Dict[str, str]:
    """
    Generate HTTP header for a request given an auth token.
    :param str auth_token: auth token to use in the header
    :return: the generated HTTP header
    :rtype: dict[str, str]
    """
    return {"Authorization": "Bearer " + auth_token} if auth_token else {}


def check_and_print_http_error(response):
    if response.status_code >= 200 and response.status_code <= 299:
        return False
    try:
        error_data = response.json()
        error_message = error_data.get("message")
        console.print(f"Error: {error_message}")
    except json.JSONDecodeError:
        console.print(f"Error Code: {response.status_code}")
        console.print(f"Error: {response.text}")

    return True


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
