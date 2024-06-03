"""
The api/v1/workspace module implements two functionalities:
- a WorkspaceRecord class that manages the local workspace information, so that
  the user does not have to call the API to get the workspace information every
  time. This class is also used by the CLI to read and write workspace info.
- a Workspace class that serves as the single entry point of all apis, holding
  information such as the url auth token, as well as caching runtime information
  such as connections. Workspace also holds ehtry points for all the apis.
"""

import os
from pydantic import BaseModel
import re
import requests
from threading import Lock
from typing import Any, Optional, Union, Dict, Tuple, Type, TypeVar, List
import yaml
import warnings

from loguru import logger

from leptonai.config import CACHE_DIR
from leptonai.util import create_cached_dir_if_needed
from leptonai.api.util import (
    _get_full_workspace_api_url,
    _get_workspace_display_name,
)

from .types.workspace import WorkspaceInfo

# import the related API resources. Note that in all these files, they should
# not import workspace to avoid circular imports.
from .photon import PhotonAPI
from .deployment import DeploymentAPI
from .job import JobAPI
from .secret import SecretAPI

from .workspace_record import WorkspaceRecord


class Workspace(object):
    def __init__(
        self,
        workspace_id: Optional[str],
        auth_token: Optional[str] = None,
        url: Optional[str] = None,
    ):
        """
        Creates a workspace api client by identifying the workspace in the following
        order:
        - If workspace_id is given, log in to the given workspace. Workspace id could
        also include the token as a complete credential string, which you can obtain
        from https://dashboard.lepton.ai/credentials.
        - If workspace_id is not given, but there is LEPTON_WORKSPACE_ID in the environment,
        log into that workspace. We will look for LEPTON_WORKSPACE_TOKEN as the auth token,
        and LEPTON_WORKSPACE_URL as the workspace url, if they exist.
        - If we have depleted all the options and still cannot determine a workspace
        id, we will throw an error.

        This function is intended to be used inside lepton deployments to log in to the
        workspace programmatically.
        """
        # First, update the workspace_id, auth_token, and url if they are None and
        # there are environment variables.
        if workspace_id is None:
            if "LEPTON_WORKSPACE_ID" in os.environ:
                workspace_id = os.environ["LEPTON_WORKSPACE_ID"]
            else:
                raise RuntimeError(
                    "You must specify workspace_id or set LEPTON_WORKSPACE_ID in the"
                    " environment. If you do not know your workspace id, go to"
                    " https://dashboard.lepton.ai/credentials and login with the"
                    " credential string."
                )
        auth_token = (
            auth_token if auth_token else os.environ.get("LEPTON_WORKSPACE_TOKEN")
        )
        # If workspace_id contains colon, it is a credential that also contains the token.
        if workspace_id and ":" in workspace_id:
            workspace_id, auth_token = workspace_id.split(":", 1)
        url = url if url else os.environ.get("LEPTON_WORKSPACE_URL")
        if url is None:
            url = _get_full_workspace_api_url(workspace_id)
        self.workspace_id: str = workspace_id
        self.auth_token: Optional[str] = auth_token
        self.url: str = url
        if not self.workspace_id:
            raise RuntimeError(
                "You must specify workspace_id or set LEPTON_WORKSPACE_ID in the"
                " environment. If you do not know your workspace id, go to"
                " https://dashboard.lepton.ai/credentials and login with the"
                " credential string."
            )
        # Creates a connection for us to use

        self._header = (
            {"Authorization": "Bearer " + self.auth_token} if self.auth_token else {}
        )
        # In default, timeout for the API calls is set to 120 seconds.
        self._timeout = 120
        self._session = requests.Session()
        if os.environ.get("LEPTON_DEBUG_HEADERS"):
            # LEPTON_DEBUG_HEADERS should be in the format of comma separated
            # header_key=header_value pairs.
            try:
                header_pairs = os.environ["LEPTON_DEBUG_HEADERS"].split(",")
                for pair in header_pairs:
                    key, value = pair.split("=")
                    self._header.setdefault(key, value)
            except:
                raise RuntimeError(
                    "LEPTON_DEBUG_HEADERS should be in the format of comma separated"
                    " header_key=header_value pairs. Got"
                    f" {os.environ['LEPTON_DEBUG_HEADERS']}"
                )

        # Add individual APIs
        self.photon = PhotonAPI(self)
        self.deployment = DeploymentAPI(self)
        self.job = JobAPI(self)
        self.secret = SecretAPI(self)

    def _safe_add(self, kwargs: Dict) -> Dict:
        if "timeout" not in kwargs:
            kwargs["timeout"] = self._timeout
        if "headers" not in kwargs:
            kwargs["headers"] = self._header
        else:
            if "Authorization" in kwargs["headers"]:
                warnings.warn("Overriding Authorization header.")
            kwargs["headers"].update(self._header)
        return kwargs

    def _get(self, path: str, *args, **kwargs):
        return self._session.get(self.url + path, *args, **self._safe_add(kwargs))

    def _post(self, path: str, *args, **kwargs):
        return self._session.post(self.url + path, *args, **self._safe_add(kwargs))

    def _patch(self, path: str, *args, **kwargs):
        return self._session.patch(self.url + path, *args, **self._safe_add(kwargs))

    def _put(self, path: str, *args, **kwargs):
        return self._session.put(self.url + path, *args, **self._safe_add(kwargs))

    def _delete(self, path: str, *args, **kwargs):
        return self._session.delete(self.url + path, *args, **self._safe_add(kwargs))

    def _head(self, path: str, *args, **kwargs):
        return self._session.head(self.url + path, *args, **self._safe_add(kwargs))

    T = TypeVar("T", bound=BaseModel)

    def ensure_type(self, response, EnsuredType: Type[T]) -> T:
        """
        Utility function to ensure that the response is of the given type.
        """
        if not response.ok:
            raise RuntimeError(
                f"API call failed with status code {response.status_code}. Details:"
                f" {response.text}"
            )
        try:
            return EnsuredType(**response.json())
        except Exception as e:
            # This should not happen: apis that use json_or_error should make sure
            # that the response is json. If this happens, it is either a programming
            # error, or the api has changed, or the lepton ai cloud side has a bug.
            raise RuntimeError(
                "You encountered a programming error. Please report this, and include"
                " the following debug info:\n*** begin of debug info ***\nresponse"
                " returned 200 OK, but the content cannot be decoded as"
                f" json.\nresponse.text: {response.text}\n\nexception"
                f" details:\n{e}\n*** end of debug info ***"
            )

    def ensure_list(self, response, EnsuredType: Type[T]) -> List[T]:
        """
        Utility function to ensure that the response is a list of the given type.
        """
        if not response.ok:
            raise RuntimeError(
                f"API call failed with status code {response.status_code}. Details:"
                f" {response.text}"
            )
        try:
            return [EnsuredType(**item) for item in response.json()]
        except Exception as e:
            # This should not happen: apis that use json_or_error should make sure
            # that the response is json. If this happens, it is either a programming
            # error, or the api has changed, or the lepton ai cloud side has a bug.
            raise RuntimeError(
                "You encountered a programming error. Please report this, and include"
                " the following debug info:\n*** begin of debug info ***\nresponse"
                " returned 200 OK, but the content cannot be decoded as"
                f" json.\nresponse.text: {response.text}\n\nexception"
                f" details:\n{e}\n*** end of debug info ***"
            )

    def ensure_ok(self, response) -> bool:
        """
        Utility function to ensure that the response is ok.
        """
        if not response.ok:
            raise RuntimeError(
                f"API call failed with status code {response.status_code}. Details:"
                f" {response.text}"
            )
        return True

    def ensure_json(self, response) -> Union[Dict, List, str]:
        """
        Utility function to ensure that the output is a json object (including dict, list, etc.)
        """
        if not response.ok:
            raise RuntimeError(
                f"API call failed with status code {response.status_code}. Details:"
                f" {response.text}"
            )
        try:
            return response.json()
        except Exception as e:
            # This should not happen: apis that use json_or_error should make sure
            # that the response is json. If this happens, it is either a programming
            # error, or the api has changed, or the lepton ai cloud side has a bug.
            raise RuntimeError(
                "You encountered a programming error. Please report this, and include"
                " the following debug info:\n*** begin of debug info ***\nresponse"
                " returned 200 OK, but the content cannot be decoded as"
                f" json.\nresponse.text: {response.text}\n\nexception"
                f" details:\n{e}\n*** end of debug info ***"
            )

    def info(self) -> WorkspaceInfo:
        """ "
        Returns the workspace info.
        """
        response = self._get("/workspace")
        return self.ensure_type(response, WorkspaceInfo)

    def version(self) -> Optional[Tuple[int, int, int]]:
        """
        Returns a tuple of (major, minor, patch) of the workspace version, or if
        this is a dev workspace, returns None.
        """
        info = self.info()
        _semver_pattern = re.compile(
            r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"  # noqa: W605
        )

        match = _semver_pattern.match(info.git_commit)
        return (
            (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            if match
            else None
        )


def current() -> Workspace:
    """
    Returns the current workspace.
    """
    return WorkspaceRecord.current()


def login(
    workspace_id: Optional[str] = None,
    auth_token: Optional[str] = None,
    url: Optional[str] = None,
) -> None:
    """
    Logs in to a workspace and saves the workspace information.
    """
    if workspace_id is None:
        if WorkspaceRecord._current_workspace_id is None:
            warnings.warn("You have not set the current workspace yet.", RuntimeWarning)
    else:
        ws = Workspace(workspace_id, auth_token, url)
        WorkspaceRecord.set_and_save(ws.workspace_id, ws.auth_token, ws.url)
