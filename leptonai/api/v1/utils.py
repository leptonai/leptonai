"""
Utility functions for the Lepton AI API.
"""

import requests
from typing import Optional, Dict

from leptonai.config import WORKSPACE_URL_RESOLVER_API, WORKSPACE_API_PATH
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


class WorkspaceNotCreatedYet(WorkspaceError):
    """
    An exception that is raised when a workspace is not created yet.
    """

    def __init__(self, workspace_id: str):
        super().__init__(f"Workspace {workspace_id} is not created yet.", workspace_id)


def _print_workspace_not_created_yet_message(workspace_id: str):
    """
    Help message to be used to print a message when a workspace is not created yet.
    """
    print(
        f"Workspace {workspace_id} is registerd, but not set up yet. To set it up,"
        f" Please visit\n  https://dashboard.lepton.ai/workspace/{workspace_id}/setup\n"
        " After that, you can log in here and use the workspace via CLI or API."
    )


def _get_workspace_display_name(workspace_id) -> Optional[str]:
    """
    Gets the workspace display name from the given workspace_id. This calls Lepton's backend server
    to get the workspace display name.

    :param str workspace_id: the workspace_id of the workspace
    :return: the workspace display name, or None if the workspace does not exist
    :raises RuntimeError: if the backend server returns an error
    :raises ValueError: if the workspace does not exist
    """

    request_body = {"id": workspace_id}
    res = requests.get(WORKSPACE_URL_RESOLVER_API, json=request_body)
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


_workspace_url_cache: Dict[str, str] = {}


def _get_full_workspace_url(workspace_id, cached=True) -> str:
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

    if cached:
        url = _workspace_url_cache.get(workspace_id)

        if url is None or not is_valid_url(url):
            url = _get_full_workspace_url(workspace_id, cached=False)
            _workspace_url_cache[workspace_id] = url

        return url

    request_body = {"id": workspace_id}
    res = requests.get(WORKSPACE_URL_RESOLVER_API, json=request_body)
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


def _get_full_workspace_api_url(workspace_id, cached=True) -> str:
    """
    Get the full URL for the API of a workspace.

    :param str workspace_id: the workspace_id of the workspace
    :return: the workspace api url, or None if the workspace does not exist
    :raises RuntimeError: if the backend server returns an error
    :raises ValueError: if the workspace does not exist
    """
    return _get_full_workspace_url(workspace_id, cached) + WORKSPACE_API_PATH
