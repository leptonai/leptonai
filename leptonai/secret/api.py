import requests
import sys
from typing import List

from leptonai.util import create_header, check_and_print_http_error


def create_remote(url: str, auth_token: str, names: List[str], values: List[str]):
    """
    Create a secret with the given name and value.

    :param str name: name of the secret
    :param str value: the value of the secret

    :return: None
    """
    request_body = [
        {"name": name, "value": value} for name, value in zip(names, values)
    ]
    response = requests.post(
        url + "/secrets", json=request_body, headers=create_header(auth_token)
    )
    if check_and_print_http_error(response):
        sys.exit(1)


def list_remote(url: str, auth_token: str):
    """
    List all secrets on a remote server.
    """
    response = requests.get(url + "/secrets", headers=create_header(auth_token))
    if check_and_print_http_error(response):
        sys.exit(1)
    return response.json()


def remove_remote(url: str, auth_token: str, name: str):
    """
    Remove a photon from a remote server.
    :param str url: url of the remote server including the schema
    (e.g. http://localhost:8000)
    :param str id: id of the photon to remove
    """
    response = requests.delete(
        url + "/secrets/" + name, headers=create_header(auth_token)
    )
    if check_and_print_http_error(response):
        sys.exit(1)
