from typing import Dict, List, Union, Optional
import warnings

from .connection import Connection
from .util import json_or_error, APIError


def list_deployment(conn: Connection) -> Union[List, APIError]:
    """
    List all deployments in a workspace.

    Returns a list of deployments.
    """
    response = conn.get("/deployments")
    # sanity check that the response is actually a list or APIError
    content = json_or_error(response)
    if isinstance(content, dict):
        return APIError(response, "You hit a programming error: response is not a list")
    return content


def remove_deployment(conn: Connection, name: str):
    """
    Remove a deployment from a workspace.

    Returns 200 if successful, 404 if the deployment does not exist.
    """
    response = conn.delete("/deployments/" + name)
    return response


def get_deployment(conn: Connection, name: str):
    """
    Get a deployment from a workspace.
    """
    response = conn.get("/deployments/" + name)
    return json_or_error(response)


def get_readiness(conn: Connection, name: str):
    """
    Get a deployment readiness info from a workspace.

    Returns the deployment info if successful, and APIError if the deployment
    does not exist.
    """
    response = conn.get("/deployments/" + name + "/readiness")
    return json_or_error(response)


def get_termination(conn: Connection, name: str):
    """
    Get a deployment termination info from a workspace.

    Returns the deployment's information about earlier terminations, if exist.
    """
    response = conn.get("/deployments/" + name + "/termination")
    return json_or_error(response)


def get_replicas(conn: Connection, name: str):
    """
    Get a deployment's replicas from a workspace.

    Returns the deployment info if successful, and APIError if the deployment
    does not exist.
    """
    response = conn.get("/deployments/" + name + "/replicas")
    return json_or_error(response)


def get_log(conn: Connection, name: str, replica: str):
    """
    Get a deployment log from a workspace.

    Returns the deployment info if successful, and APIError if the deployment
    does not exist.
    """
    response = conn.get(
        "/deployments/" + name + "/replicas/" + replica + "/log",
        stream=True,  # stream the response
        timeout=None,  # no timeout
    )
    if response.ok:
        for chunk in response.iter_content(chunk_size=None):
            if chunk:
                yield chunk.decode("utf8")
    else:
        return APIError(response)


def update_deployment(
    conn: Connection,
    name: str,
    photon_id: Optional[str] = None,
    min_replicas: Optional[int] = None,
    resource_shape: Optional[str] = None,
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
    if min_replicas is not None:
        deployment_body["resource_requirement"] = {}
        deployment_body["resource_requirement"]["min_replicas"] = min_replicas
    if resource_shape:
        if "resource_requirement" not in deployment_body:
            deployment_body["resource_requirement"] = {}
        deployment_body["resource_requirement"]["resource_shape"] = resource_shape
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
    response = conn.patch(
        "/deployments/" + name,
        json=deployment_body,
    )
    return json_or_error(response)


def get_qps(conn: Connection, name: str, by_path: bool = False):
    """
    Get a deployment's QPS from a workspace.

    Returns the deployment info if successful, and APIError if the deployment
    does not exist.
    """
    if by_path:
        response = conn.get(
            "/deployments/" + name + "/monitoring/FastAPIQPSByPath",
        )
    else:
        response = conn.get(
            "/deployments/" + name + "/monitoring/FastAPIQPS",
        )
    return json_or_error(response)


def get_latency(conn: Connection, name: str, by_path: bool = False):
    """
    Get a deployment's latency from a workspace.

    Returns the deployment info if successful, and APIError if the deployment
    does not exist.
    """
    if by_path:
        response = conn.get(
            "/deployments/" + name + "/monitoring/FastAPILatencyByPath",
        )
    else:
        response = conn.get(
            "/deployments/" + name + "/monitoring/FastAPILatency",
        )
    return json_or_error(response)
