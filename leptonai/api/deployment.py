import requests

from .util import create_header, json_or_error


def list_deployment(url: str, auth_token: str):
    """
    List all deployments in a workspace.

    Returns a list of deployments.
    """
    response = requests.get(url + "/deployments", headers=create_header(auth_token))
    return json_or_error(response)


def remove_deployment(url: str, auth_token: str, name: str):
    """
    Remove a deployment from a workspace.

    Returns 200 if successful, 404 if the deployment does not exist.
    """
    response = requests.delete(
        url + "/deployments/" + name, headers=create_header(auth_token)
    )
    return response
