"""
Utility functions for the Lepton AI API.
"""

import requests
from typing import Optional, Dict

from leptonai.config import (
    DGXC_WORKSPACE_API_PATH,
    DGXC_WORKSPACE_URL_RESOLVER_API,
    WORKSPACE_URL_RESOLVER_API,
    WORKSPACE_API_PATH,
    API_URL_BASE,
)
from leptonai.util import is_valid_url


class WorkspaceError(RuntimeError):
    def __init__(self, message, workspace_id=None, workspace_url=None, auth_token=None):
        super().__init__(message)
        self.workspace_id = workspace_id
        self.workspace_url = workspace_url
        self.auth_token = auth_token

    def __str__(self):
        details = ", ".join(
            f"{key.replace('_', ' ').title()}: {value}"
            for key, value in vars(self).items()
            if value and key != "args"
        )
        return f"{self.args[0]} ({details})" if details else self.args[0]


class WorkspaceUnauthorizedError(WorkspaceError):
    def __init__(self, workspace_id=None, workspace_url=None, auth_token=None):
        super().__init__(
            "Unauthorized access to the workspace",
            workspace_id,
            workspace_url,
            auth_token,
        )


class WorkspaceNotFoundError(WorkspaceError):
    def __init__(self, workspace_id=None, workspace_url=None, auth_token=None):
        super().__init__(
            "Workspace not found. If the workspace was just created, please wait"
            " for 10 minutes. Contact us if the workspace remains unavailable after"
            " 10 minutes.",
            workspace_id,
            workspace_url,
            auth_token,
        )


class WorkspaceForbiddenError(WorkspaceError):
    def __init__(self, workspace_id=None, workspace_url=None, auth_token=None):
        super().__init__(
            "Forbidden access to the workspace",
            workspace_id,
            workspace_url,
            auth_token,
        )


class WorkspaceNotCreatedYet(WorkspaceError):
    """
    An exception that is raised when a workspace is not created yet.
    """

    def __init__(self, workspace_id: str):
        super().__init__(f"Workspace {workspace_id} is not created yet.", workspace_id)


class WorkspaceConfigurationError(WorkspaceError):
    """
    Raised when local workspace configuration is missing or invalid
    (e.g., missing workspace_id/token/url).
    """

    def __init__(
        self,
        message: str,
        workspace_id: Optional[str] = None,
        workspace_url: Optional[str] = None,
        auth_token: Optional[str] = None,
    ):
        super().__init__(message, workspace_id, workspace_url, auth_token)


def _print_workspace_not_created_yet_message(workspace_id: str):
    """
    Help message to be used to print a message when a workspace is not created yet.
    """
    print(
        f"Workspace {workspace_id} is registered, but not set up yet. To set it up,"
        f" Please visit\n  https://dashboard.lepton.ai/workspace/{workspace_id}/setup\n"
        " After that, you can log in here and use the workspace via CLI or API."
    )


def _get_workspace_display_name(
    workspace_id, url=None, is_lepton_classic=False, token=None
) -> Optional[str]:
    """
    Gets the workspace display name from the given workspace_id. This calls Lepton's backend server
    to get the workspace display name.

    :param str workspace_id: the workspace_id of the workspace
    :return: the workspace display name, or None if the workspace does not exist
    :raises RuntimeError: if the backend server returns an error
    :raises ValueError: if the workspace does not exist
    """

    resolver_api = (
        WORKSPACE_URL_RESOLVER_API
        if is_lepton_classic
        else DGXC_WORKSPACE_URL_RESOLVER_API + "/" + workspace_id
    )
    if url:
        resolver_api = url

    if is_lepton_classic:
        request_body = {"id": workspace_id}
        res = requests.get(resolver_api, json=request_body)
    else:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        res = requests.get(resolver_api, headers=headers)

    if not res.ok:
        raise RuntimeError(
            f"Lepton server returned an error: {res.status_code} {res.content}."
        )
    elif res.content == b"":
        raise RuntimeError(f"Cannot find the workspace with id {workspace_id}.")
    else:
        content = res.json()
        if isinstance(content, list) or "display_name" not in content:
            raise RuntimeError(
                "You hit a programming error: response is not a dictionary. Please"
                " report this and include the following information: url:"
                f" {WORKSPACE_URL_RESOLVER_API}, request_body: {request_body},"
                f" response: {res}."
            )
        return content["display_name"]


def _get_token_expires_at(workspace_id, url=None, token=None) -> Optional[int]:
    """
    Gets the token expires at from the given workspace_id. This calls Lepton's backend server
    to get the token expires at.
    """
    # Build resolver URL
    url = DGXC_WORKSPACE_URL_RESOLVER_API + "/" + workspace_id if url is None else url
    url += "/tokens"

    headers = {"Authorization": f"Bearer {token}"} if token else {}
    res = requests.get(url, headers=headers)
    if not res.ok:
        raise RuntimeError(
            f"Lepton server returned an error: {res.status_code} {res.content}."
        )
    elif res.content == b"":
        raise RuntimeError(f"Cannot find the workspace with id {workspace_id}.")
    else:
        content = res.json()
        if not isinstance(content, list):
            raise RuntimeError("Unable to get tokens info.")

        if not token:
            raise RuntimeError("Unable to match tokens info.")

        candidate_expires: list[int] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            mv = item.get("masked_value")
            ea = item.get("expires_at")
            if not isinstance(mv, str) or "..." not in mv or not isinstance(ea, int):
                continue
            left, right = mv.split("...", 1)
            if token.startswith(left) and token.endswith(right):
                candidate_expires.append(ea)

        if not candidate_expires:
            raise RuntimeError("No match tokens info.")
        return min(candidate_expires)


_workspace_url_cache: Dict[str, str] = {}


def _get_full_workspace_url(workspace_id, cached=True, is_lepton_classic=False) -> str:
    """
    Gets the workspace url from the given workspace_id. This calls Lepton's backend server
    to get the workspace url.

    The workspace url is different from the workspace api url: the workspace url is the url
    that the client uses to call deployments, while the workspace api url is used to call
    the Lepton API.

    :param str workspace_id: the workspace_id of the workspace
    :return: the workspace url, or None if the workspace does not exist
    :raises RuntimeError: if the backend server returns an error
    :raises ValueError: if the workspace does not exist
    """
    if not is_lepton_classic:
        return API_URL_BASE

    # Process the lepton classic workspace url

    if cached:
        url = _workspace_url_cache.get(workspace_id)

        if url is None or not is_valid_url(url):
            url = _get_full_workspace_url(
                workspace_id, cached=False, is_lepton_classic=is_lepton_classic
            )
            _workspace_url_cache[workspace_id] = url

        return url
    request_body = {"id": workspace_id}
    res = requests.get(
        WORKSPACE_URL_RESOLVER_API,
        json=request_body,
    )
    if not res.ok:
        raise RuntimeError(
            f"Lepton server returned an error: {res.status_code} {res.content}."
        )
    elif res.content == b"":
        raise RuntimeError(f"Cannot find the workspace with id {workspace_id}.")
    else:
        content = res.json()
        if (not isinstance(content, dict)) or "url" not in content:
            raise RuntimeError(
                "You hit a programming error: response is not a dictionary. Please"
                " report this and include the following information: url:"
                f" {WORKSPACE_URL_RESOLVER_API}, request_body: {request_body},"
                f" response: {res}."
            )
        elif content["url"] == "":
            raise WorkspaceNotCreatedYet(workspace_id)
        return content["url"]


def _get_full_workspace_api_url(
    workspace_id, cached=True, is_lepton_classic=False
) -> str:
    """
    Get the full URL for the API of a workspace.

    :param str workspace_id: the workspace_id of the workspace
    :return: the workspace api url, or None if the workspace does not exist
    :raises RuntimeError: if the backend server returns an error
    :raises ValueError: if the workspace does not exist
    """
    workspace_api_path = (
        DGXC_WORKSPACE_API_PATH if not is_lepton_classic else WORKSPACE_API_PATH
    )

    url = (
        _get_full_workspace_url(workspace_id, cached, is_lepton_classic)
        + workspace_api_path
    )
    if not is_lepton_classic:
        url += workspace_id
    return url


def _get_workspace_origin_url(url: str) -> str:
    """
    Get the origin url of a workspace.
    """
    # For DGXC workspaces, the origin url is the url.
    if "dgxc" in url:
        return url
    # For classic workspaces, origin url is not required.
    return None
