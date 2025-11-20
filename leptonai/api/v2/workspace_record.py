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
from loguru import logger

from leptonai.config import CACHE_DIR
from leptonai.util import create_cached_dir_if_needed
from .utils import (
    _get_full_workspace_api_url,
    _get_workspace_display_name,
    _get_token_expires_at,
    WorkspaceNotCreatedYet,
    _get_workspace_origin_url,
    _print_workspace_not_created_yet_message,
    WorkspaceConfigurationError,
)

# so we avoid circular imports
if TYPE_CHECKING:
    from .client import APIClient


class LocalWorkspaceInfo(BaseModel):
    id_: Optional[str] = Field(None, alias="id")
    url: str
    display_name: Optional[str] = None
    auth_token: Optional[str] = None
    workspace_origin_url: Optional[str] = None
    is_lepton_classic: Optional[bool] = False
    token_expires_at: Optional[int] = None


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
        workspace_url = os.environ.get("LEPTON_WORKSPACE_URL")
        workspace_origin_url = os.environ.get("LEPTON_WORKSPACE_ORIGIN_URL")
        if workspace_id:
            cls.set(workspace_id, auth_token, workspace_url, workspace_origin_url)
        else:
            raise WorkspaceConfigurationError(
                "LEPTON_WORKSPACE_ID environment variable is not set. Please set it to"
                " the workspace id you want to log in to."
            )

    @classmethod
    def set(
        cls,
        workspace_id: str,
        auth_token: Optional[str] = None,
        url: Optional[str] = None,
        workspace_origin_url: Optional[str] = None,
        is_lepton_classic: Optional[bool] = None,
        could_be_new_token: Optional[bool] = False,
    ):
        """
        Sets a workspace by adding it to the workspace info file.
        """
        display_name = (
            None
            if workspace_id not in cls._singleton_record.workspaces
            else cls._singleton_record.workspaces[workspace_id].display_name
        )
        token_expires_at = (
            None
            if (
                workspace_id not in cls._singleton_record.workspaces
                or could_be_new_token
            )
            else cls._singleton_record.workspaces[workspace_id].token_expires_at
        )

        # _get_workspace_display_name is called in two scenarios:
        # 1. Initial CLI login without URL (for both DGXC and CLASSIC workspaces will use default urls)
        # 2. CLI login with URL (will use input url)
        #    Note: This works for DGXC as the resolver api URL matches the workspace URL.
        #    Future workspace types may require additional modifications.
        if not display_name:
            try:
                display_name = _get_workspace_display_name(
                    workspace_id,
                    url=url,
                    is_lepton_classic=is_lepton_classic,
                    token=auth_token,
                )
            except RuntimeError as e:
                logger.trace(
                    "Failed to fetch workspace display name"
                    f" (workspace_id={workspace_id}, url={url},"
                    f" is_lepton_classic={is_lepton_classic}): {e}"
                )
                display_name = None
        if token_expires_at is None and not is_lepton_classic:
            try:
                token_expires_at = _get_token_expires_at(
                    workspace_id,
                    url=url,
                    token=auth_token,
                )
            except RuntimeError as e:
                logger.trace(
                    f"Failed to fetch token expiration (workspace_id={workspace_id},"
                    f" url={url}): {e}"
                )
                token_expires_at = None
        if url is None:
            url = _get_full_workspace_api_url(
                workspace_id, is_lepton_classic=is_lepton_classic
            )
        if not workspace_origin_url:
            workspace_origin_url = _get_workspace_origin_url(url)
        # Create workspace info with optional workspace_origin_url
        cls._singleton_record.workspaces[workspace_id] = LocalWorkspaceInfo(
            id=workspace_id,
            url=url,
            display_name=display_name,
            auth_token=auth_token,
            workspace_origin_url=workspace_origin_url,
            is_lepton_classic=is_lepton_classic,
            token_expires_at=token_expires_at,
        )
        cls._singleton_record.current_workspace = workspace_id
        cls._save_to_file()

    @classmethod
    def set_or_exit(
        cls,
        workspace_id: str,
        auth_token: Optional[str] = None,
        url: Optional[str] = None,
        workspace_origin_url: Optional[str] = None,
        is_lepton_classic: Optional[bool] = None,
        could_be_new_token: Optional[bool] = False,
    ):
        """
        Sets a workspace, and if it is not set up yet, print a message and exit.
        This should only be used in CLI.
        """
        try:
            cls.set(
                workspace_id,
                auth_token,
                url,
                workspace_origin_url,
                is_lepton_classic,
                could_be_new_token,
            )
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
                raise WorkspaceConfigurationError(
                    "You have not specified a workspace id, and have not set the"
                    " current workspace either."
                )
        if workspace_id in cls._singleton_record.workspaces:
            from .client import APIClient

            ws = cls._singleton_record.workspaces[workspace_id]
            return APIClient(
                ws.id_,
                ws.auth_token,
                ws.url,
                ws.workspace_origin_url,
                ws.is_lepton_classic,
            )
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
        else:
            raise WorkspaceConfigurationError("You are not logged in to any workspace.")
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

    @classmethod
    def get_dashboard_base_url(
        cls, workspace_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Returns the base dashboard URL derived from the current workspace URL.
        """
        info = cls.get(workspace_id) if workspace_id else cls.current()
        if not info or info.is_lepton_classic:
            return None
        base = (info.url or "").replace("://gateway", "://dashboard", 1)
        base = base.replace("/api/v2", "", 1)
        base = base.replace("/workspaces", "/workspace", 1)
        return base

    @classmethod
    def refresh_token_expires_at(
        cls,
        workspace_id: Optional[str] = None,
        skip_if_token_exists: Optional[bool] = False,
    ) -> Optional[int]:
        workspace_id = workspace_id if workspace_id else cls.get_current_workspace_id()

        skip_flag = (
            skip_if_token_exists
            or workspace_id is None
            or not cls.has(workspace_id)
            or cls.get(workspace_id).token_expires_at is not None
        )
        if skip_flag:
            return cls.get(workspace_id).token_expires_at

        info = cls.get(workspace_id)
        if not info or info.is_lepton_classic:
            return None
        try:
            token_expires_at = _get_token_expires_at(
                workspace_id,
                url=info.url,
                token=info.auth_token,
            )
        except Exception as e:
            logger.trace(
                f"Failed to refresh token expires at for workspace {workspace_id} with"
                f" error: {e}"
            )
            return None
        info.token_expires_at = token_expires_at
        cls._save_to_file()
        return token_expires_at


# When importing, read the content of the workspace info file as initialization.
WorkspaceRecord._load_workspace_record()
