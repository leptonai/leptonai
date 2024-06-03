"""
The WorkspaceRecord class manages the local workspace information, so that
the user does not have to call the API to get the workspace information every
time. This class is also used by the CLI to read and write workspace info.
"""

from threading import Lock
from typing import Any, Optional, Union, Dict
import yaml

from leptonai.config import CACHE_DIR
from leptonai.util import create_cached_dir_if_needed
from leptonai.api.util import (
    _get_full_workspace_api_url,
    _get_workspace_display_name,
)


class WorkspaceRecord(object):
    """
    Internal class to manage the local
    """

    _singleton_dict: Dict[str, Any] = {"workspaces": {}, "current_workspace": None}
    # global lock for reading and writing the workspace info file
    _rw_lock = Lock()
    WORKSPACE_FILE = CACHE_DIR / "workspace_info.yaml"

    def __init__(self):
        raise RuntimeError("WorkspaceInfoLocalRecord should not be instantiated.")

    @classmethod
    def load_workspace_info(cls):
        if cls.WORKSPACE_FILE.exists():
            with cls._rw_lock:
                with open(cls.WORKSPACE_FILE) as f:
                    cls._singleton_dict = yaml.safe_load(f)

    @classmethod
    def reload(cls):
        cls.load_workspace_info()

    @classmethod
    def _save_to_file(cls):
        create_cached_dir_if_needed()
        with cls._rw_lock:
            with open(cls.WORKSPACE_FILE, "w") as f:
                yaml.safe_dump(cls._singleton_dict, f)

    @classmethod
    def set_and_save(
        cls,
        workspace_id: str,
        auth_token: Optional[str] = None,
        url: Optional[str] = None,
    ):
        """
        Saves a workspace by adding it to the workspace info file.
        """
        try:
            display_name = _get_workspace_display_name(workspace_id)
        except RuntimeError:
            display_name = ""
        cls._singleton_dict["workspaces"][workspace_id] = {}
        if url is None:
            url = _get_full_workspace_api_url(workspace_id)
        cls._singleton_dict["workspaces"][workspace_id]["url"] = url
        cls._singleton_dict["workspaces"][workspace_id]["display_name"] = display_name
        cls._singleton_dict["workspaces"][workspace_id]["auth_token"] = auth_token
        cls.set_current(workspace_id)
        cls._save_to_file()

    @classmethod
    def has(cls, workspace_id: str):
        return workspace_id in cls._singleton_dict["workspaces"]

    @classmethod
    def _current_workspace_id(cls) -> Union[str, None]:
        return cls._singleton_dict["current_workspace"]

    @classmethod
    def get(cls, workspace_id: str):
        try:
            ws = cls._singleton_dict["workspaces"][workspace_id]
        except KeyError:
            raise
        # so we avoid circular imports
        from .workspace import Workspace

        return Workspace(workspace_id, ws["auth_token"], ws["url"])

    @classmethod
    def current(cls):
        name = cls._current_workspace_id()
        if name is None:
            raise RuntimeError("You have not set the current workspace yet.")
        else:
            return cls.get(name)

    @classmethod
    def set_current(cls, workspace_id: Optional[str] = None):
        """
        Sets the current workspace to the given workspace_id, or None if no workspace_id is given.
        """
        if workspace_id and workspace_id not in cls._singleton_dict["workspaces"]:
            raise ValueError(f"Workspace {workspace_id} does not exist.")
        cls._save_to_file()

    @classmethod
    def remove(cls, workspace_id: str):
        """
        Removes the workspace with the given workspace_id.
        """
        cls._singleton_dict["workspaces"].pop(workspace_id)
        if cls._singleton_dict["current_workspace"] == workspace_id:
            cls._singleton_dict["current_workspace"] = None
        cls._save_to_file()


# When importing, read the content of the workspace info file as initialization.
WorkspaceRecord.load_workspace_info()
