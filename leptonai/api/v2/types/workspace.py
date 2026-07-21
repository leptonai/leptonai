from enum import Enum
from pydantic import BaseModel
from typing import Dict, Optional

from loguru import logger

from .quota import TotalResource


class WorkspaceState(str, Enum):
    Normal = "normal"
    Paused = "paused"
    AllPodsTerminated = "all-pods-terminated"
    Terminated = "terminated"
    Unknown = "unknown"

    @classmethod
    def _missing_(cls, value):
        logger.trace(f"Unknown value: {value} for WorkspaceState")
        return cls.Unknown


class Workloads(BaseModel):
    num_deployments: int
    num_jobs: int
    num_pods: int
    num_secrets: int
    num_image_pull_secrets: int


class ResourceShape(BaseModel):
    description: Optional[str] = None
    cpu: Optional[float] = None
    memory: Optional[int] = None
    accelerator_type: Optional[str] = None
    accelerator_num: Optional[float] = None
    accelerator_fraction: Optional[float] = None


class ResourceQuota(BaseModel):
    limit: TotalResource
    used: TotalResource


class WorkspaceFeatures(BaseModel):
    """Workspace feature flags.

    Mirrors the backend ``go-pkg/workspace-features`` ``WorkspaceFeatures``
    struct. Only the flags the CLI acts on are enumerated; any additional
    flags the backend adds are ignored here. ``enable_new_deployment_api``
    switches the endpoint/devpod command paths from the legacy
    ``/deployments`` routes to the new ``/endpoints`` and ``/devpods`` routes.
    """

    enable_new_deployment_api: Optional[bool] = None


class WorkspaceInfo(BaseModel):
    # Implementation note: inlined version.Info in the go backend.
    build_time: str
    git_commit: str

    # main info
    workspace_name: str
    workspace_tier: str
    workspace_state: WorkspaceState
    supported_shapes: Dict[str, ResourceShape]
    not_in_use: Optional[bool] = None
    workspace_disk_usage_bytes: int
    workloads: Workloads
    resource_quota: ResourceQuota
    dedicated_node_group_only: Optional[bool] = None

    # The backend nests all workspace feature flags under a "features" object in
    # the /workspace (and /info) response (api-server/httpapi/info/handler.go
    # WorkspaceInfo.Features). Absent on older backends -> None -> legacy mode.
    features: Optional[WorkspaceFeatures] = None
