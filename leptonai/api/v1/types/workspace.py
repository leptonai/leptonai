from enum import Enum
from pydantic import BaseModel
from typing import Dict, Optional

from .quota import TotalResource, TotalService


class WorkspaceState(str, Enum):
    Normal = "normal"
    Paused = "paused"
    AllPodsTerminated = "all-pods-terminated"
    Terminated = "terminated"


class Workloads(BaseModel):
    num_photons: int
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


class ServiceQuota(BaseModel):
    limit: TotalService
    used: TotalService


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
    service_quota: ServiceQuota
    dedicated_node_group_only: Optional[bool] = None
