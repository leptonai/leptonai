from typing import List, Union, Optional, Dict
import warnings

from loguru import logger

from . import types
from .connection import Connection
from .util import json_or_error, APIError


warnings.warn(
    "the leptonai.api.deployment module is deprecated. Use leptonai.api.v1.types for a"
    " more fine grained API service. This backward compatible code might be removed"
    " in the future.",
    DeprecationWarning,
    stacklevel=2,
)


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
    ret = json_or_error(response)
    assert isinstance(ret, (dict, APIError))
    return ret


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


def make_token_vars_from_config(
    is_public: Optional[bool], tokens: Optional[List[str]]
) -> Optional[List[types.TokenVar]]:
    # Note that None is different from [] here. None means that the tokens are not
    # changed, while [] means that the tokens are cleared (aka, public deployment)
    if is_public is None and tokens is None:
        return None
    elif is_public and tokens:
        raise ValueError(
            "For access control, you cannot specify both is_public and token at the"
            " same time. Please specify either is_public=True with no tokens passed"
            " in, or is_public=False and tokens as a list."
        )
    else:
        if is_public:
            return []
        else:
            final_tokens = [
                types.TokenVar(
                    value_from=types.TokenValue(token_name_ref="WORKSPACE_TOKEN")
                )
            ]
            if tokens:
                final_tokens.extend([types.TokenVar(value=token) for token in tokens])
            return final_tokens


def update_deployment(
    conn: Connection,
    name: str,
    photon_id: Optional[str] = None,
    photon_namespace: Optional[str] = None,
    min_replicas: Optional[int] = None,
    resource_shape: Optional[str] = None,
    is_public: Optional[bool] = None,
    tokens: Optional[List[str]] = None,
    no_traffic_timeout: Optional[int] = None,
) -> Union[APIError, Dict]:
    """
    Update a deployment in a workspace.

    Currently only supports updating the photon id, the min replicas, and the api tokens.
    For any more complex changes, consider re-run the deployment.
    """
    deployment_user_spec = types.DeploymentUserSpec(
        photon_id=photon_id,
        photon_namespace=photon_namespace,
        resource_requirement=types.ResourceRequirement(
            resource_shape=resource_shape,
            min_replicas=min_replicas,
        ),
        api_tokens=make_token_vars_from_config(
            is_public=is_public,
            tokens=tokens,
        ),
        auto_scaler=(
            None
            if no_traffic_timeout is None
            else types.AutoScaler(
                scale_down=types.ScaleDown(no_traffic_timeout=no_traffic_timeout)
            )
        ),
    )
    deployment_spec = types.Deployment(
        metadata=types.Metadata(id=name, name=name),
        spec=deployment_user_spec,
    )
    logger.trace(f"deployment_spec:\n{deployment_spec}")

    deployment_body = deployment_spec.dict(exclude_none=True, by_alias=True)
    if not deployment_body:
        # If nothing is updated...
        warnings.warn(
            "There is nothing to update - did you forget to pass in any arguments?"
        )
    response = conn.patch(
        "/deployments/" + name,
        json=deployment_body,
    )
    ret = json_or_error(response)
    assert isinstance(ret, (dict, APIError))
    return ret


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
