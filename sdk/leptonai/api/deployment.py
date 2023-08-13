import requests
from typing import Dict, List, Union, Optional
import warnings

from .util import create_header, json_or_error, APIError


def list_deployment(url: str, auth_token: Optional[str]) -> Union[List, APIError]:
    """
    List all deployments in a workspace.

    Returns a list of deployments.
    """
    response = requests.get(url + "/deployments", headers=create_header(auth_token))
    # sanity check that the response is actually a list or APIError
    content = json_or_error(response)
    if isinstance(content, dict):
        return APIError(response, "You hit a programming error: response is not a list")
    return content


def remove_deployment(url: str, auth_token: Optional[str], name: str):
    """
    Remove a deployment from a workspace.

    Returns 200 if successful, 404 if the deployment does not exist.
    """
    response = requests.delete(
        url + "/deployments/" + name, headers=create_header(auth_token)
    )
    return response


def get_deployment(url: str, auth_token: Optional[str], name: str):
    """
    Get a deployment from a workspace.
    """
    response = requests.get(
        url + "/deployments/" + name, headers=create_header(auth_token)
    )
    return json_or_error(response)


def get_readiness(url: str, auth_token: Optional[str], name: str):
    """
    Get a deployment readiness info from a workspace.

    Returns the deployment info if successful, and APIError if the deployment
    does not exist.
    """
    response = requests.get(
        url + "/deployments/" + name + "/readiness", headers=create_header(auth_token)
    )
    return json_or_error(response)


def get_termination(url: str, auth_token: Optional[str], name: str):
    """
    Get a deployment termination info from a workspace.

    Returns the deployment's information about earlier terminations, if exist.
    """
    response = requests.get(
        url + "/deployments/" + name + "/termination", headers=create_header(auth_token)
    )
    return json_or_error(response)


def get_replicas(url: str, auth_token: Optional[str], name: str):
    """
    Get a deployment's replicas from a workspace.

    Returns the deployment info if successful, and APIError if the deployment
    does not exist.
    """
    response = requests.get(
        url + "/deployments/" + name + "/replicas", headers=create_header(auth_token)
    )
    return json_or_error(response)


def get_log(url: str, auth_token: Optional[str], name: str, replica: str):
    """
    Get a deployment log from a workspace.

    Returns the deployment info if successful, and APIError if the deployment
    does not exist.
    """
    response = requests.get(
        url + "/deployments/" + name + "/replicas/" + replica + "/log",
        headers=create_header(auth_token),
        stream=True,  # stream the response
    )
    if response.ok:
        for chunk in response.iter_content(chunk_size=None):
            if chunk:
                yield chunk.decode("utf8")
    else:
        return APIError(response)


def update_deployment(
    url: str,
    auth_token: Optional[str],
    name: str,
    photon_id: Optional[str] = None,
    min_replicas: Optional[int] = None,
    api_tokens: Optional[List[Dict[str, Union[str, Dict[str, str]]]]] = None,
):
    """
    Update a deployment in a workspace.

    Currently only supports updating the photon id, the min replicas, and the api tokens.
    For any more complex changes, consider re-run the deployment.
    """
    deployment_body = {}
    if photon_id:
        deployment_body["photon_id"] = photon_id
    if min_replicas:
        deployment_body["resource_requirement"] = {}
        deployment_body["resource_requirement"]["min_replicas"] = min_replicas
    # Note that if the user passed in an empty list, it is still different from "None":
    # None means the user did not want to update the api tokens, while an empty list means
    # the user wants to remove api tokens and make it public.
    if api_tokens is not None:
        deployment_body["api_tokens"] = api_tokens
    if not deployment_body:
        # If nothing is updated...
        warnings.warn(
            "There is nothing to update - did you forget to pass in any arguments?"
        )
    response = requests.patch(
        url + "/deployments/" + name,
        headers=create_header(auth_token),
        json=deployment_body,
    )
    return json_or_error(response)


def get_qps(url: str, auth_token: Optional[str], name: str, by_path: bool = False):
    """
    Get a deployment's QPS from a workspace.

    Returns the deployment info if successful, and APIError if the deployment
    does not exist.
    """
    if by_path:
        response = requests.get(
            url + "/deployments/" + name + "/monitoring/FastAPIQPSByPath",
            headers=create_header(auth_token),
        )
    else:
        response = requests.get(
            url + "/deployments/" + name + "/monitoring/FastAPIQPS",
            headers=create_header(auth_token),
        )
    return json_or_error(response)


def get_latency(url: str, auth_token: Optional[str], name: str, by_path: bool = False):
    """
    Get a deployment's latency from a workspace.

    Returns the deployment info if successful, and APIError if the deployment
    does not exist.
    """
    if by_path:
        response = requests.get(
            url + "/deployments/" + name + "/monitoring/FastAPILatencyByPath",
            headers=create_header(auth_token),
        )
    else:
        response = requests.get(
            url + "/deployments/" + name + "/monitoring/FastAPILatency",
            headers=create_header(auth_token),
        )
    return json_or_error(response)
