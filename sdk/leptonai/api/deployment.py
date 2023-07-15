import requests

from .util import create_header, json_or_error, APIError


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


def get_deployment(url: str, auth_token: str, name: str):
    """
    Get a deployment from a workspace.
    """
    response = requests.get(
        url + "/deployments/" + name, headers=create_header(auth_token)
    )
    return json_or_error(response)


def get_readiness(url: str, auth_token: str, name: str):
    """
    Get a deployment readiness info from a workspace.

    Returns the deployment info if successful, and APIError if the deployment
    does not exist.
    """
    response = requests.get(
        url + "/deployments/" + name + "/readiness", headers=create_header(auth_token)
    )
    return json_or_error(response)


def get_termination(url: str, auth_token: str, name: str):
    """
    Get a deployment termination info from a workspace.

    Returns the deployment's information about earlier terminations, if exist.
    """
    response = requests.get(
        url + "/deployments/" + name + "/termination", headers=create_header(auth_token)
    )
    return json_or_error(response)


def get_replicas(url: str, auth_token: str, name: str):
    """
    Get a deployment's replicas from a workspace.

    Returns the deployment info if successful, and APIError if the deployment
    does not exist.
    """
    response = requests.get(
        url + "/deployments/" + name + "/replicas", headers=create_header(auth_token)
    )
    return json_or_error(response)


def get_log(url: str, auth_token: str, name: str, replica: str):
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
        for chunk in response.iter_content(chunk_size=1):
            if chunk:
                yield chunk.decode("utf8")
    else:
        return APIError(response)


def update_deployment(url: str, auth_token: str, name: str, replicas: int):
    """
    Update a deployment in a workspace.

    Currently only supports updating the replicas. We may support photon id
    in the future.
    """
    deployment_body = {
        "resource_requirement": {
            "min_replicas": replicas,
        },
    }
    response = requests.patch(
        url + "/deployments/" + name,
        headers=create_header(auth_token),
        json=deployment_body,
    )
    return json_or_error(response)


def get_qps(url: str, auth_token: str, name: str, by_path: bool = False):
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


def get_latency(url: str, auth_token: str, name: str, by_path: bool = False):
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
