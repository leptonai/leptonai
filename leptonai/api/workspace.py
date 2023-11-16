import os
import re
from typing import Any, Optional, Union, Dict, Tuple
import yaml

from leptonai.config import CACHE_DIR
from leptonai.util import create_cached_dir_if_needed
from .connection import Connection
from .util import (
    APIError,
    json_or_error,
    _get_full_workspace_api_url,
    _get_workspace_display_name,
    _get_full_workspace_url,
)


class WorkspaceInfoLocalRecord(object):
    _singleton_dict: Dict[str, Any] = {"workspaces": {}, "current_workspace": None}
    _singleton_conn: Optional[Connection] = None
    WORKSPACE_FILE = CACHE_DIR / "workspace_info.yaml"

    def __init__(self):
        raise RuntimeError("WorkspaceInfoLocalRecord should not be instantiated.")

    @classmethod
    def load_workspace_info(cls):
        if cls.WORKSPACE_FILE.exists():
            with open(cls.WORKSPACE_FILE) as f:
                cls._singleton_dict = yaml.safe_load(f)

    @classmethod
    def _save_to_file(cls):
        create_cached_dir_if_needed()
        with open(cls.WORKSPACE_FILE, "w") as f:
            yaml.safe_dump(cls._singleton_dict, f)

    @classmethod
    def get_all_workspaces(cls):
        return cls._singleton_dict["workspaces"]

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
    def set_current(cls, workspace_id: Optional[str] = None):
        """
        Sets the current workspace to the given workspace_id, or None if no workspace_id is given.
        """
        if workspace_id and workspace_id not in cls._singleton_dict["workspaces"]:
            raise ValueError(f"Workspace {workspace_id} does not exist.")
        cls._singleton_dict["current_workspace"] = workspace_id
        # When we set the current workspace, we also set the connection.
        if workspace_id:
            cls._singleton_conn = Connection(
                cls._singleton_dict["workspaces"][workspace_id]["url"],
                cls._singleton_dict["workspaces"][workspace_id]["auth_token"],
            )
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

    @classmethod
    def get_current_workspace_id(cls) -> Optional[str]:
        """
        Gets the current workspace id.
        """
        return cls._singleton_dict["current_workspace"]

    @classmethod
    def get_current_connection(cls) -> Connection:
        """
        Gets the current workspace connection.
        """
        if cls._singleton_conn is None:
            url = cls._get_current_workspace_api_url()
            if url is None:
                raise RuntimeError(
                    "It seems that you are not logged in to any workspace yet."
                    " Please log in and then retry. To log in, use `lep login`"
                    " from the commandline."
                )
            auth_token = cls.get_current_workspace_token()
            cls._singleton_conn = Connection(url, auth_token)
        return cls._singleton_conn

    @classmethod
    def _get_current_workspace_api_url(cls) -> Optional[str]:
        """
        Gets the current workspace url.
        """
        workspace_id = cls._singleton_dict["current_workspace"]
        if workspace_id is None:
            return None
        workspaces = cls._singleton_dict["workspaces"]
        return workspaces[workspace_id]["url"]

    @classmethod
    def _get_current_workspace_deployment_url(cls) -> Optional[str]:
        """
        Gets the current workspace url that can be used to call deployments.
        """
        workspace_id = cls._singleton_dict["current_workspace"]
        if workspace_id is None:
            return None
        # Note: the workspace url is different from the workspace api url.
        # Todo: cache this url.
        return _get_full_workspace_url(workspace_id)

    @classmethod
    def _get_current_workspace_display_name(cls) -> Optional[str]:
        """
        Gets the current workspace display name.
        """
        workspace_id = cls._singleton_dict["current_workspace"]
        if workspace_id is None:
            return None
        workspaces = cls._singleton_dict["workspaces"]
        return workspaces[workspace_id]["display_name"]

    @classmethod
    def get_current_workspace_token(cls) -> Optional[str]:
        """
        Gets the current workspace auth token.
        """
        workspace_id = cls._singleton_dict["current_workspace"]
        if workspace_id is None:
            return None
        workspaces = cls._singleton_dict["workspaces"]
        return workspaces[workspace_id]["auth_token"]


# When importing, read the content of the workspace info file as initialization.
WorkspaceInfoLocalRecord.load_workspace_info()


def current_connection() -> Connection:
    return WorkspaceInfoLocalRecord.get_current_connection()


def login(
    workspace_id: Optional[str] = None,
    auth_token: Optional[str] = None,
    url: Optional[str] = None,
):
    """
    Logs in to a workspace in the following order:
    - If workspace_id is given, log in to the given workspace.
    - If workspace_id is not given, but there is LEPTON_WORKSPACE_ID in the environment,
      log into that workspace. We will look for LEPTON_WORKSPACE_TOKEN as the auth token,
      and LEPTON_WORKSPACE_URL as the workspace url, if they exist.
    - Otherwise, produce an error.

    This function is intended to be used inside lepton deployments to log in to the
    workspace programmatically.
    """
    if workspace_id:
        WorkspaceInfoLocalRecord.set_and_save(workspace_id, auth_token, url)
    elif "LEPTON_WORKSPACE_ID" in os.environ:
        WorkspaceInfoLocalRecord.set_and_save(
            os.environ["LEPTON_WORKSPACE_ID"],
            auth_token=os.environ.get("LEPTON_WORKSPACE_TOKEN", None),
            url=os.environ.get("LEPTON_WORKSPACE_URL", None),
        )
    else:
        raise RuntimeError(
            "You must specify workspace_id or set LEPTON_WORKSPACE_ID in the"
            " environment."
        )


def get_workspace_info(conn: Optional[Connection] = None) -> Union[APIError, Dict]:
    """
    Gets the runtime information for the given workspace url.
    """
    conn = conn if conn else current_connection()
    response = conn.get("/workspace")
    info = json_or_error(response)
    assert isinstance(info, (dict, APIError))
    return info


_semver_pattern = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"  # noqa: W605
)


def version(conn: Optional[Connection] = None) -> Optional[Tuple[int, int, int]]:
    """
    Gets the version of the given workspace url, in a tuple (major, minor, patch).

    If this is a dev workspace, this will return None as we don't support versioning for dev workspaces.
    """
    conn = conn if conn else current_connection()
    response = conn.get("/workspace")
    info = json_or_error(response)
    assert isinstance(info, (dict, APIError))
    if isinstance(info, APIError):
        return None
    else:
        match = _semver_pattern.match(info["git_commit"])
        return (
            (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            if match
            else None
        )
