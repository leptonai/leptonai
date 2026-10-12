"""Workspace API client used by CLI commands, including worker threads."""

from typing import Optional

from leptonai.api.v2.client import APIClient as _APIClient


class APIClient(_APIClient):
    def __init__(
        self,
        workspace_id: Optional[str] = None,
        auth_token: Optional[str] = None,
        url: Optional[str] = None,
        workspace_origin_url: Optional[str] = None,
    ):
        super().__init__(
            workspace_id=workspace_id,
            auth_token=auth_token,
            url=url,
            workspace_origin_url=workspace_origin_url,
            client_type="cli",
        )
