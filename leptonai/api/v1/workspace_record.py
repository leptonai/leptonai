"""
The WorkspaceRecord class manages the local workspace information, so that
the user does not have to call the API to get the workspace information every
time. This class is also used by the CLI to read and write workspace info.
"""

import os
import sys
from pydantic import BaseModel, Field
from threading import Lock
from typing import Optional, Union, Dict, TYPE_CHECKING, List
import yaml

from leptonai.config import CACHE_DIR
from leptonai.util import create_cached_dir_if_needed
from .utils import (
    _get_full_workspace_api_url,
    _get_workspace_display_name,
    WorkspaceNotCreatedYet,
    _print_workspace_not_created_yet_message,
)

# so we avoid circular imports
if TYPE_CHECKING:
    from .client import APIClient


class LocalWorkspaceInfo(BaseModel):
    id_: Optional[str] = Field(None, alias="id")
    url: str
    display_name: Optional[str] = None
    auth_token: Optional[str] = None


class _LocalWorkspaceRecord(BaseModel):
    workspaces: Dict[str, LocalWorkspaceInfo] = {}
    current_workspace: Optional[str] = None


class WorkspaceRecord(object):
    """
    Internal class to manage the local workspace records objects.
    """

    _singleton_record: _LocalWorkspaceRecord = _LocalWorkspaceRecord()
    # global lock for reading and writing the workspace info file
    _rw_lock = Lock()
    WORKSPACE_FILE = CACHE_DIR / "workspace_info.yaml"

    def __init__(self):
        raise RuntimeError("WorkspaceInfoLocalRecord should not be instantiated.")

    @classmethod
    def _load_workspace_record(cls):
        if cls.WORKSPACE_FILE.exists():
            with cls._rw_lock:
                with open(cls.WORKSPACE_FILE) as f:
                    cls._singleton_record = _LocalWorkspaceRecord(**yaml.safe_load(f))
        # Backward compatiblitity: for all the workspace info, the old way is to
        # not store the workspace id in the field, and we used to store it only in
        # the key. In the current way, we store the workspace id in the field as well.
        # So, if we detect that the workspace id is not in the field, we will add it.
        for k, v in cls._singleton_record.workspaces.items():
            if v.id_ is None:
                v.id_ = k

    @classmethod
    def reload(cls):
        """
        Reloads the local workspace record
        """
        cls._load_workspace_record()

    @classmethod
    def _save_to_file(cls):
        create_cached_dir_if_needed()
        with cls._rw_lock:
            with open(cls.WORKSPACE_FILE, "w") as f:
                yaml.safe_dump(cls._singleton_record.dict(by_alias=True), f)

    @classmethod
    def login_with_env(cls):
        """
        Logs in to the workspace using the environmental variables.
        """
        workspace_id = os.environ.get("LEPTON_WORKSPACE_ID")
        auth_token = os.environ.get("LEPTON_WORKSPACE_TOKEN")
        if workspace_id:
            cls.set(workspace_id, auth_token)
        else:
            raise RuntimeError(
                "LEPTON_WORKSPACE_ID environment variable is not set. Please set it to"
                " the workspace id you want to log in to."
            )

    @classmethod
    def set(
        cls,
        workspace_id: str,
        auth_token: Optional[str] = None,
        url: Optional[str] = None,
    ):
        """
        Sets a workspace by adding it to the workspace info file.
        """
        try:
            display_name = _get_workspace_display_name(workspace_id)
        except RuntimeError:
            display_name = None
        if url is None:
            url = _get_full_workspace_api_url(workspace_id)
        cls._singleton_record.workspaces[workspace_id] = LocalWorkspaceInfo(
            id=workspace_id, url=url, display_name=display_name, auth_token=auth_token
        )
        cls._singleton_record.current_workspace = workspace_id
        cls._save_to_file()

    @classmethod
    def set_or_exit(
        cls,
        workspace_id: str,
        auth_token: Optional[str] = None,
        url: Optional[str] = None,
    ):
        """
        Sets a workspace, and if it is not set up yet, print a message and exit.
        This should only be used in CLI.
        """
        try:
            cls.set(workspace_id, auth_token, url)
        except WorkspaceNotCreatedYet:
            _print_workspace_not_created_yet_message(workspace_id)
            sys.exit(1)

    @classmethod
    def workspaces(cls) -> List[LocalWorkspaceInfo]:
        return list(cls._singleton_record.workspaces.values())

    @classmethod
    def has(cls, workspace_id: str):
        return workspace_id in cls._singleton_record.workspaces

    @classmethod
    def get(cls, workspace_id: str) -> Union[None, LocalWorkspaceInfo]:
        return cls._singleton_record.workspaces.get(workspace_id)

    @classmethod
    def current(cls) -> Union[None, LocalWorkspaceInfo]:
        """
        Returns the information of the current workspace, or None if no current workspace is set.
        """
        return (
            cls.get(cls._singleton_record.current_workspace)
            if cls._singleton_record.current_workspace
            else None
        )

    @classmethod
    def client(cls, workspace_id: Optional[str] = None) -> "APIClient":
        """
        Creates a client that can be used to interact with the workspace.
        """
        if not workspace_id:
            workspace_id = cls._singleton_record.current_workspace
            if workspace_id is None:
                raise RuntimeError(
                    "You have not specified a workspace id, and have not set the"
                    " current workspace either."
                )
        if workspace_id in cls._singleton_record.workspaces:
            from .client import APIClient

            ws = cls._singleton_record.workspaces[workspace_id]
            return APIClient(ws.id_, ws.auth_token, ws.url)
        else:
            raise ValueError(
                f"Workspace {workspace_id} does not exist in the local record."
            )

    @classmethod
    def logout(cls, purge: bool = False):
        """
        Logs out of the current workspace.
        """
        if cls._singleton_record.current_workspace:
            if purge:
                cls.remove(cls._singleton_record.current_workspace)
            else:
                cls._singleton_record.current_workspace = None
        cls._save_to_file()

    @classmethod
    def remove(cls, workspace_id: str):
        """
        Removes the workspace with the given workspace_id.
        """
        cls._singleton_record.workspaces.pop(workspace_id)
        if cls._singleton_record.current_workspace == workspace_id:
            cls._singleton_record.current_workspace = None
        cls._save_to_file()

    @classmethod
    def get_current_workspace_id(cls) -> Optional[str]:
        current_workspace = cls.current()
        return current_workspace.id_ if current_workspace else None


# When importing, read the content of the workspace info file as initialization.
WorkspaceRecord._load_workspace_record()
