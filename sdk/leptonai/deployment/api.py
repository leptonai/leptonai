import requests
import sys

from leptonai.util import create_header, check_and_print_http_error


def list_remote(url: str, auth_token: str):
    """
    List all deployments on a remote server.
    """
    response = requests.get(url + "/deployments", headers=create_header(auth_token))
    if check_and_print_http_error(response):
        sys.exit(1)
    return response.json()


def remove_remote(url: str, auth_token: str, name: str):
    """
    Remove a deployment from a remote server.
    """
    response = requests.delete(
        url + "/deployments/" + name, headers=create_header(auth_token)
    )
    if check_and_print_http_error(response):
        sys.exit(1)
