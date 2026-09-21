"""Teleport SSH targets and connection metadata published by the Pod API."""

from typing import Literal

from pydantic import BaseModel, Field


class TeleportTarget(BaseModel):
    name: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    proxy: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9.-]*$")
    port: int = Field(strict=True, ge=1, le=65535)
    cluster_domain: str = Field(
        alias="clusterDomain", pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$"
    )
    username: str = Field(pattern=r"^[a-zA-Z0-9_][a-zA-Z0-9._-]*$")


class TeleportConnection(TeleportTarget):
    status: Literal["Running", "NotRunning"]
