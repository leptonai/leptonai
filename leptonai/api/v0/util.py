"""
Utility functions for the Lepton AI API.
"""

import json
import requests
from typing import Dict, List, Optional, Union

from leptonai.config import WORKSPACE_URL_RESOLVER_API, WORKSPACE_API_PATH
from leptonai.util import is_valid_url


class APIError(object):
    """
    An error class for API calls that return status other than 200.
    """

    def __init__(self, response: requests.Response, message: Optional[str] = None):
        self.status_code = response.status_code
        self.message = message if message else response.text

    def __str__(self) -> str:
        return f"APIError (API response code {self.status_code}): {self.message}"


def json_or_error(
    response: requests.Response, additional_debug_info: str = ""
) -> Union[Dict, List, APIError]:
    """
    A utility function to return json if the response is ok, and otherwise returns an APIError object
    that details the error encountered.

    This function is intended to be used to wrap raw api functions and parse the response, which should
    contain a json response if the response is ok.

    :param requests.Response response: the response to parse
    :return: the json content of the response if the response is ok, otherwise an APIError or NotJsonError
    """
    if response.ok:
        try:
            return response.json()
        except json.JSONDecodeError:
            # This should not happen: apis that use json_or_error should make sure
            # that the response is json. If this happens, it is either a programming
            # error, or the api has changed, or the lepton ai cloud side has a bug.
            return APIError(
                response,
                message=(
                    "You encountered a programming error. Please report this, and"
                    " include the following debug info:\n*** begin of debug info"
                    f" ***\n{additional_debug_info}\nresponse returned 200 OK, but the"
                    " content cannot be decoded as json.\nresponse.text:"
                    f" {response.text}\n\n*** end of debug info ***"
                ),
            )
    else:
        return APIError(response)


def create_header(auth_token: Optional[str]) -> Dict[str, str]:
    """
    Generate HTTP header for a request given an auth token.

    :param str auth_token: auth token to use in the header. None if the request does not require an auth token.
    :return: the generated HTTP header
    :rtype: dict[str, str]
    """
    return {"Authorization": "Bearer " + auth_token} if auth_token else {}


class WorkspaceNotCreatedYet(RuntimeError):
    """
    An exception that is raised when a workspace is not created yet.
    """

    def __init__(self, workspace_id: str):
        super().__init__(f"Workspace {workspace_id} is not created yet.")


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


_workspace_url_cache = {}


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
