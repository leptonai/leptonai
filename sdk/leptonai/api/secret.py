import requests
from typing import List

from .util import create_header, json_or_error


def create_secret(url: str, auth_token: str, names: List[str], values: List[str]):
    """
    Create a secret with the given name and value.

    :param str name: name of the secret
    :param str value: the value of the secret

    :return: the response from the server
    """
    request_body = [
        {"name": name, "value": value} for name, value in zip(names, values)
    ]
    response = requests.post(
        url + "/secrets", json=request_body, headers=create_header(auth_token)
    )
    return response


def list_secret(url: str, auth_token: str):
    """
    List all secrets on a workspace.
    """
    response = requests.get(url + "/secrets", headers=create_header(auth_token))
    return json_or_error(response)


def remove_secret(url: str, auth_token: str, name: str):
    """
    Remove a secret from a workspace.
    """
    response = requests.delete(
        url + "/secrets/" + name, headers=create_header(auth_token)
    )
    return response
