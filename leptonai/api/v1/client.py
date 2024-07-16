"""
The api/v1/client module serves as the single entry point of all apis, holding
information such as the url auth token, as well as caching runtime objects
such as http sessions.
"""

import os
import re
import requests
from typing import Optional, Union, Dict, Tuple

from .object_storage import ObjectStorageAPI

from .types.workspace import WorkspaceInfo

# import the related API resources. Note that in all these files, they should
# not import workspace to avoid circular imports.
from .api_resource import APIResourse
from .dedicated_node_groups import DedicatedNodeGroupAPI
from .photon import PhotonAPI
from .deployment import DeploymentAPI
from .job import JobAPI
from .secret import SecretAPI
from .kv import KVAPI
from .queue import QueueAPI
from .pod import PodAPI
from .ingress import IngressAPI
from .storage import StorageAPI


from .utils import (
    _get_full_workspace_api_url,
    WorkspaceUnauthorizedError,
    WorkspaceNotFoundError,
)
from .workspace_record import WorkspaceRecord


class APIClient(object):
    """
    A Lepton API client that is associated with a workspace. This class holds all
    the apis callable by the user.
    """

    def __init__(
        self,
        workspace_id: Optional[str] = None,
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
        # We will resolve workspace id in the following order:
        #  - user specified one
        #  - environment variable LEPTON_WORKSPACE_ID
        #  - current workspace of the workspace record
        # and if there is still no choice, we will throw an error.
        workspace_id = (
            workspace_id
            or os.environ.get("LEPTON_WORKSPACE_ID")
            or (WorkspaceRecord.current().id_ if WorkspaceRecord.current() else None)
        )
        if workspace_id is None:
            raise RuntimeError(
                "You must specify workspace_id or set LEPTON_WORKSPACE_ID in the"
                " environment, or use commandline `lep login` to log in to a "
                " workspace. If you do not know your workspace credentials, go to"
                " https://dashboard.lepton.ai/credentials and login with the"
                " credential string."
            )
        # If workspace_id contains colon, it is a credential that also contains the token.
        if ":" in workspace_id and not auth_token:
            workspace_id, auth_token = workspace_id.split(":", 1)
        # We will then resolve the auth token in the following order:
        # - user specified one
        # - environment variable LEPTON_WORKSPACE_TOKEN
        # - auth token of the workspace record
        auth_token = (
            auth_token
            or os.environ.get("LEPTON_WORKSPACE_TOKEN")
            or (
                WorkspaceRecord.get(workspace_id).auth_token  # type: ignore
                if WorkspaceRecord.has(workspace_id)
                else None
            )
        )
        # We will then resolve the url in a similar order.
        url = (
            url
            or os.environ.get("LEPTON_WORKSPACE_URL")
            or (
                WorkspaceRecord.get(workspace_id).url  # type: ignore
                if WorkspaceRecord.has(workspace_id)
                else None
            )
            or _get_full_workspace_api_url(workspace_id)
        )
        self.workspace_id: str = workspace_id
        self.auth_token: Optional[str] = auth_token
        self.url: str = url

        # Creates a connection for us to use.
        self._header = {}
        if self.auth_token:
            self._header["Authorization"] = "Bearer " + self.auth_token
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
            except ValueError:
                raise RuntimeError(
                    "LEPTON_DEBUG_HEADERS should be in the format of comma separated"
                    " header_key=header_value pairs. Got"
                    f" {os.environ['LEPTON_DEBUG_HEADERS']}"
                )

        # Add individual APIs
        self.nodegroup = DedicatedNodeGroupAPI(self)
        self.photon = PhotonAPI(self)
        self.deployment = DeploymentAPI(self)
        self.job = JobAPI(self)
        self.pod = PodAPI(self)
        self.secret = SecretAPI(self)
        self.kv = KVAPI(self)
        self.queue = QueueAPI(self)
        self.ingress = IngressAPI(self)
        self.storage = StorageAPI(self)
        self.object_storage = ObjectStorageAPI(self)

    def _safe_add(self, kwargs: Dict) -> Dict:
        """
        Internal utility function to add default values to the kwargs.
        """
        kwargs.setdefault("headers", self._header)
        kwargs.setdefault("timeout", self._timeout)
        # if kwargs does have headers, but does not have Authorization, we will add it.
        for k, v in self._header.items():
            kwargs["headers"].setdefault(k, v)
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

    def info(self) -> WorkspaceInfo:
        """
        Returns the workspace info.
        """
        ws_api = APIResourse(self)
        response = self._get("/workspace")
        auth_token_hint = (
            self.auth_token[:2] + "****" + self.auth_token[-2:]
            if self.auth_token
            else ""
        )

        if response.status_code == 401:
            raise WorkspaceUnauthorizedError(
                workspace_id=self.workspace_id,
                workspace_url=self.url,
                auth_token=auth_token_hint,
            )

        if response.status_code == 404:
            raise WorkspaceNotFoundError(
                workspace_id=self.workspace_id,
                workspace_url=self.url,
                auth_token=auth_token_hint,
            )

        return ws_api.ensure_type(response, WorkspaceInfo)

    def version(self) -> Optional[Tuple[int, int, int]]:
        """
        Returns a tuple of (major, minor, patch) of the workspace version, or if
        this is a dev workspace, returns None.
        """
        info = self.info()
        _semver_pattern = re.compile(
            r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"  # noqa: E501
            # noqa: W605
        )

        match = _semver_pattern.match(info.git_commit)
        return (
            (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            if match
            else None
        )

    def token(self) -> Union[str, None]:
        """
        Returns the current workspace token.
        """
        return self.auth_token

    def get_workspace_id(self) -> Union[str, None]:
        return self.workspace_id

    def get_workspace_name(self) -> Union[str, None]:
        return WorkspaceRecord.current().display_name
