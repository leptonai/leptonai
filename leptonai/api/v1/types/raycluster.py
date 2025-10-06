from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from loguru import logger

from leptonai.config import compatible_field_validator, v2only_field_validator

from .affinity import LeptonResourceAffinity
from .common import Metadata, LeptonUserSecurityContext
from .deployment import EnvVar, Mount, QueueConfig, ReservationConfig


class RayClusterCommonGroupSpec(BaseModel):
    """
    Base spec shared by head and worker groups.
    """

    accelerator_fraction: Optional[float] = None
    accelerator_memory: Optional[int] = None
    accelerator_num: Optional[float] = None
    accelerator_pass_all: Optional[bool] = None
    accelerator_type: Optional[str] = None
    affinity: Optional[LeptonResourceAffinity] = None

    cpu: Optional[float] = None
    memory: Optional[int] = None
    ephemeral_storage_in_gb: Optional[int] = None
    shared_memory_size: Optional[int] = None

    host_network: Optional[bool] = None
    enable_rdma: Optional[bool] = None
    is_adaptive: Optional[bool] = None

    min_replicas: Optional[int] = None
    max_replicas: Optional[int] = None

    resource_shape: Optional[str] = None

    envs: Optional[List[EnvVar]] = None
    mounts: Optional[List[Mount]] = None
    queue_config: Optional[QueueConfig] = None
    user_security_context: Optional[LeptonUserSecurityContext] = None
    reservation_config: Optional[ReservationConfig] = None

    @compatible_field_validator("min_replicas")
    def validate_min_replicas(cls, min_replicas):
        if min_replicas is None:
            return min_replicas
        if min_replicas < 0:
            raise ValueError(
                f"min_replicas must be non-negative. Found {min_replicas}."
            )
        return min_replicas

    @v2only_field_validator("max_replicas")
    def validate_max_replicas(cls, max_replicas, values: "ValidationInfo"):  # type: ignore # noqa: F821
        if max_replicas is None:
            return max_replicas
        if max_replicas < 0:
            raise ValueError(
                f"max_replicas must be non-negative. Found {max_replicas}."
            )
        if "min_replicas" not in values.data:
            raise ValueError(
                "min_replicas must be specified if max_replicas is specified."
            )
        min_replicas = values.data["min_replicas"]
        if min_replicas > max_replicas:
            raise ValueError(
                "min_replicas must be smaller than max_replicas. Found"
                f" min_replicas={min_replicas}, max_replicas={max_replicas}."
            )
        return max_replicas


class RayHeadGroupSpec(RayClusterCommonGroupSpec):
    """
    Spec for the head node group.
    """


class RayWorkerGroupSpec(RayClusterCommonGroupSpec):
    """
    Spec for a worker node group.
    """

    group_name: Optional[str] = None


class RayAutoscaler(BaseModel):
    """
    Spec for the Ray autoscaler.
    """

    ray_worker_idle_timeout: Optional[int] = None


class RayHeadInfo(BaseModel):
    """
    Information about the Ray head node service/pod.
    """

    pod_ip: Optional[str] = Field(default=None, alias="podIP")
    pod_name: Optional[str] = Field(default=None, alias="podName")
    service_ip: Optional[str] = Field(default=None, alias="serviceIP")
    service_name: Optional[str] = Field(default=None, alias="serviceName")


class RayK8sCondition(BaseModel):
    """
    Standard Kubernetes condition used by many resources.
    """

    last_transition_time: str = Field(alias="lastTransitionTime")
    message: str
    reason: str
    status: str
    type_: str = Field(alias="type")
    observed_generation: Optional[int] = Field(default=None, alias="observedGeneration")


class LeptonRayClusterState(str, Enum):
    Ready = "Ready"
    NotReady = "Not Ready"
    Starting = "Starting"
    Deleting = "Deleting"
    Scaling = "Scaling"
    Unknown = ""

    @classmethod
    def _missing_(cls, value):
        logger.trace(f"Unknown value: {value} for LeptonRayClusterState")
        return cls.Unknown


class LeptonRayClusterUserSpec(BaseModel):
    """
    LeptonRayCluster user-facing spec only.
    """

    image: Optional[str] = None
    image_pull_secrets: Optional[List[str]] = None
    ray_version: Optional[str] = None
    suspend: Optional[bool] = None
    head_group_spec: Optional[RayHeadGroupSpec] = None
    worker_group_specs: Optional[List[RayWorkerGroupSpec]] = None
    autoscaler: Optional[RayAutoscaler] = None


class LeptonRayClusterStatus(BaseModel):
    """
    LeptonRayCluster status as observed from the controller.
    """

    # Using Optional[str] for k8s IntOrString fields to accommodate both forms
    desiredCPU: Optional[str] = None
    desiredGPU: Optional[str] = None
    desiredMemory: Optional[str] = None

    availableWorkerReplicas: Optional[int] = None
    desiredWorkerReplicas: Optional[int] = None
    maxWorkerReplicas: Optional[int] = None
    minWorkerReplicas: Optional[int] = None
    readyWorkerReplicas: Optional[int] = None

    endpoints: Optional[Dict[str, str]] = None
    head: Optional[RayHeadInfo] = None

    lastUpdateTime: Optional[str] = None
    observedGeneration: Optional[int] = None

    state: LeptonRayClusterState

    conditions: Optional[List[RayK8sCondition]] = None


class LeptonRayCluster(BaseModel):
    metadata: Optional[Metadata] = None
    spec: Optional[LeptonRayClusterUserSpec] = None
    status: Optional[LeptonRayClusterStatus] = None
