import requests
from typing import Optional
import yaml

from leptonai.config import CACHE_DIR, WORKSPACE_URL_RESOLVER_API, WORKSPACE_API_PATH
from .util import APIError, create_header, json_or_error

WORKSPACE_FILE = CACHE_DIR / "workspace_info.yaml"


def load_workspace_info():
    """
    Loads the workspace info file.
    """
    workspace_info = {"workspaces": {}, "current_workspace": None}
    if WORKSPACE_FILE.exists():
        with open(WORKSPACE_FILE) as f:
            workspace_info = yaml.safe_load(f)
    return workspace_info


def _get_full_workspace_url(workspace_id) -> Optional[str]:
    """
    Gets the workspace url from the given workspace_id. This calls Lepton's backend server
    to get the workspace url.

    In most cases, you should not be calling this function directly. Instead, use
    :func:`get_full_workspace_api_url` to get the workspace API url.

    :param str workspace_id: the workspace_id of the workspace
    :return: the workspace url, or None if the workspace does not exist
    :raises RuntimeError: if the backend server returns an error
    """
    request_body = {"id": workspace_id}
    response = json_or_error(
        requests.get(WORKSPACE_URL_RESOLVER_API, json=request_body)
    )
    if isinstance(response, APIError):
        raise RuntimeError(
            "Failed to connect to the Lepton server. Did you connect to the internet?"
        )
    if response == {}:
        return None
    else:
        # TODO: do we assume that the format returned by the server is always correct?
        return response["url"]


def get_full_workspace_api_url(workspace_id) -> Optional[str]:
    """
    Get the full URL for the API of a workspace.

    :param str workspace_id: the workspace_id of the workspace
    :return: the workspace api url, or None if the workspace does not exist
    :raises APIError: if the backend server returns an error
    """
    workspace_url = _get_full_workspace_url(workspace_id)
    return workspace_url + WORKSPACE_API_PATH if workspace_url else None


def save_workspace(workspace_id, url, terraform_dir=None, auth_token=None):
    """
    Saves a workspace by adding it to the workspace info file.
    """
    workspace_info = load_workspace_info()
    workspace_info["workspaces"][workspace_id] = {}
    workspace_info["workspaces"][workspace_id]["url"] = url
    workspace_info["workspaces"][workspace_id]["terraform_dir"] = terraform_dir
    workspace_info["workspaces"][workspace_id]["auth_token"] = auth_token

    with open(WORKSPACE_FILE, "w") as f:
        yaml.safe_dump(workspace_info, f)


def remove_workspace(workspace_id):
    """
    Removes the workspace with the given workspace_id.
    """
    workspace_info = load_workspace_info()
    workspace_info["workspaces"].pop(workspace_id)
    if workspace_info["current_workspace"] == workspace_id:
        workspace_info["current_workspace"] = None
    with open(WORKSPACE_FILE, "w") as f:
        yaml.safe_dump(workspace_info, f)


def set_current_workspace(workspace_id=None):
    """
    Sets the current workspace to the given workspace_id, or None if no workspace_id is given.
    """
    workspace_info = load_workspace_info()
    if workspace_id and workspace_id not in workspace_info["workspaces"]:
        raise ValueError(f"Workspace {workspace_id} does not exist.")
    workspace_info["current_workspace"] = workspace_id
    with open(WORKSPACE_FILE, "w") as f:
        yaml.safe_dump(workspace_info, f)


def get_auth_token(workspace_url) -> Optional[str]:
    """
    Gets the current workspace auth token.
    """
    #  TODO: Store current auth token in yaml for constant time access
    workspace_info = load_workspace_info()
    for _, vals in workspace_info["workspaces"].items():
        if vals["url"] == workspace_url:
            return vals["auth_token"]
    else:
        return None


def get_workspace():
    """
    Gets the current workspace.
    """
    workspace_info = load_workspace_info()
    return workspace_info["current_workspace"]


def get_current_workspace_url() -> Optional[str]:
    """
    Gets the current workspace url.
    """
    workspace_info = load_workspace_info()
    current_workspace = workspace_info["current_workspace"]
    if current_workspace is None:
        return None
    workspaces = workspace_info["workspaces"]
    return workspaces[current_workspace]["url"]


def get_workspace_info(url: str, auth_token: str):
    """
    List all secrets on a workspace.
    """
    response = requests.get(url + "/workspace", headers=create_header(auth_token))
    return json_or_error(response)
