from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List

from .common import Metadata


class VolumeFrom(str, Enum):
    Local = "local"
    Remote = "remote"


class VolumeCreationMode(str, Enum):
    Mount = "mount"
    Mkdir = "mkdir"


class MountOptions(BaseModel):
    mount_workload_type: Optional[str] = None
    host_mount_cache_group_net_if: Optional[str] = None
    host_mount_target_cache_disk_num: Optional[int] = None
    host_mount_cache_size_in_mib: Optional[int] = None


class Volume(BaseModel):
    from_: VolumeFrom = Field(..., alias="from")
    name: str
    size_in_gb: int
    mount_options: Optional[MountOptions] = None
    creation_mode: Optional[VolumeCreationMode] = None
    from_path: Optional[str] = None
    default_mount_path: Optional[str] = None


class AllocationModeType(str, Enum):
    Auto = "auto"
    Static = "static"


class SchedulingPolicy(BaseModel):
    pod_stacking_first: Optional[bool] = None


class NodeGroupOwner(str, Enum):
    Empty = ""
    Customer = "customer"
    Lepton = "lepton"


class NetworkConfigurations(BaseModel):
    external_endpoint_subdomain: Optional[str] = None
    public_net_interfaces: Optional[List[str]] = None
    private_net_interfaces: Optional[List[str]] = None


class SlackChannel(BaseModel):
    channel: str


class AlertNotificationConfig(BaseModel):
    slack_channel: Optional[SlackChannel] = None


class DedicatedNodeGroupSpec(BaseModel):
    # Inlined LepotnDedicatedNodeGroupUserSpec
    workspaces: Optional[List[str]] = None
    volumes: Optional[List[Volume]] = None
    allocation_mode: AllocationModeType
    infini_band_enabled: Optional[bool] = None
    scheduling_policy: Optional[SchedulingPolicy] = None
    owner: Optional[NodeGroupOwner] = None
    networking: Optional[NetworkConfigurations] = None
    alert_notification_config: Optional[AlertNotificationConfig] = None

    # additonal properties
    gpu_product: Optional[str] = None
    desired_nodes: Optional[int] = None


class DedicatedNodeGroupStatus(BaseModel):
    ready_nodes: int


class DedicatedNodeGroup(BaseModel):
    metadata: Metadata
    spec: DedicatedNodeGroupSpec
    status: DedicatedNodeGroupStatus


# Node definitions from cluster-api-server/httpapi/type_node.go


class NodeResourceCPU(BaseModel):
    type_: Optional[str] = Field(None, alias="type")
    allocated: Optional[float] = None
    total: Optional[float] = None


class NodeResourceMemory(BaseModel):
    allocated: Optional[int] = None
    total: Optional[int] = None


class NodeResourceGPU(BaseModel):
    product: Optional[str] = None
    allocated: Optional[float] = None
    total: Optional[float] = None


class NodeResourceDisk(BaseModel):
    # TODO: get the current disk usage and total
    pass


class NodeResourceSystem(BaseModel):
    os: Optional[str] = None
    kernel_version: Optional[str] = None
    cuda_version: Optional[str] = None
    cuda_driver_version: Optional[str] = None


class NodeResourceWorkload(BaseModel):
    type_: str = Field(..., alias="type")
    name: str
    id_: str = Field(..., alias="id")
    replica_id: str
    workspace: str
    cpu: Optional[float] = None
    memory: Optional[int] = None
    gpu_count: Optional[float] = None


class NodeResource(BaseModel):
    cpu: Optional[NodeResourceCPU] = None
    gpu: Optional[NodeResourceGPU] = None
    memory: Optional[NodeResourceMemory] = None
    disk: Optional[NodeResourceDisk] = None
    system: Optional[NodeResourceSystem] = None


class NodeSpec(BaseModel):
    dedicated_node_group: Optional[str] = None
    public_op: Optional[str] = None
    resource: Optional[NodeResource] = None
    unschedulable: bool


class NodeStatus(BaseModel):
    status: Optional[List[str]] = None
    workloads: Optional[List[NodeResourceWorkload]] = None


class Node(BaseModel):
    metadata: Metadata
    spec: NodeSpec
    status: Optional[NodeStatus]
