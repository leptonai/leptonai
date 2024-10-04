import warnings
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List

from leptonai.config import compatible_field_validator, v2only_field_validator

from .affinity import LeptonResourceAffinity
from .common import Metadata

DEFAULT_STORAGE_VOLUME_NAME = "default"


class EnvValue(BaseModel):
    secret_name_ref: Optional[str] = None


class EnvVar(BaseModel):
    name: str
    value: Optional[str] = None
    value_from: Optional[EnvValue] = None


class MountOptions(BaseModel):
    local_cache_size_mib: Optional[int] = None
    read_only: Optional[bool] = None


class Mount(BaseModel):
    path: Optional[str] = None
    from_: Optional[str] = Field(default=None, alias="from")
    mount_path: str
    mount_options: Optional[MountOptions] = None


class ContainerPort(BaseModel):
    """
    The port spec of a Lepton Job.
    """

    container_port: int
    protocol: Optional[str] = None
    host_port: Optional[int] = None
    enable_load_balancer: Optional[bool] = None

    @compatible_field_validator("container_port")
    def validate_container_port(cls, v):
        if v < 0 or v > 65535:
            raise ValueError("Invalid port number. Port must be between 0 and 65535.")
        return v

    @compatible_field_validator("protocol")
    def validate_protocol(cls, v):
        if v and v.lower() not in ["tcp", "udp"]:
            raise ValueError(
                f"Invalid protocol: {v}. Protocol must be either tcp or udp."
            )
        return v if v is None else v.lower()


class LeptonContainer(BaseModel):
    """
    The container spec of a Lepton Job.
    """

    image: Optional[str] = None
    ports: Optional[List[ContainerPort]] = None
    command: Optional[List[str]] = None


class LeptonMetrics(BaseModel):
    """
    The metrics spec of a Lepton Job.
    """

    disable_pulling_from_replica: Optional[bool] = None


# Spec to hold resource requirements
class ResourceRequirement(BaseModel):
    resource_shape: Optional[str] = None

    # resource requirements per replica
    cpu: Optional[float] = None
    memory: Optional[int] = None
    ephemeral_storage_in_gb: Optional[int] = None
    accelerator_type: Optional[str] = None
    accelerator_num: Optional[float] = None

    shared_memory_size: Optional[int] = None

    # Deprecated: Please use affinity.
    resourse_affinity: Optional[str] = None

    affinity: Optional[LeptonResourceAffinity] = None
    min_replicas: Optional[int] = None
    max_replicas: Optional[int] = None
    host_network: Optional[bool] = None

    @compatible_field_validator("resource_shape")
    def validate_resource_shape(cls, v):
        if v is None:
            return v
        v = v.lower()
        # due to the following message being a bit too noisy, we will comment it out
        # for now till a later time when the resource shapes are more constrained.
        # if v not in VALID_SHAPES:
        #     # We will check if the user passed in a valid shape, and if not, we will
        #     # print a warning.
        #     # However, we do not want to directly go to an error, because there might
        #     # be cases when the CLI and the cloud service is out of sync. For example
        #     # if the user environment has an older version of the CLI while the cloud
        #     # service has been updated to support more shapes, we want to allow the
        #     # user to use the new shapes. One can simply ignore the warning and proceed.
        #     warnings.warn(
        #         "It seems that you passed in a non-standard resource shape"
        #         f" {v}. Valid shapes supported by the CLI are:\n"
        #         f" {', '.join(VALID_SHAPES)}"
        #     )
        return v

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


class ScaleDown(BaseModel):
    no_traffic_timeout: Optional[int] = None
    not_ready_timeout: Optional[int] = None

    @compatible_field_validator("no_traffic_timeout")
    def validate_no_traffic_timeout(cls, v):
        if v is not None and v < 0:
            raise ValueError(f"no_traffic_timeout must be non-negative. Found {v}.")
        return v

    @compatible_field_validator("not_ready_timeout")
    def validate_not_ready_timeout(cls, v):
        if v is not None and v < 0:
            raise ValueError(f"not_ready_timeout must be non-negative. Found {v}.")
        return v


class AutoscalerTargetThroughput(BaseModel):
    qpm: Optional[float] = None
    paths: Optional[List[str]] = None
    methods: Optional[List[str]] = None


class AutoScaler(BaseModel):
    scale_down: Optional[ScaleDown] = None
    target_gpu_utilization_percentage: Optional[int] = None
    target_throughput: Optional[AutoscalerTargetThroughput] = None

    @compatible_field_validator("target_gpu_utilization_percentage")
    def validate_target_gpu_utilization_percentage(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError(
                "target_gpu_utilization_percentage must be between 0 and 100. Found"
                f" {v}."
            )
        return v


class TokenValue(BaseModel):
    token_name_ref: str


class TokenVar(BaseModel):
    value: Optional[str] = None
    value_from: Optional[TokenValue] = None


class HealthCheckReadiness(BaseModel):
    require_approval: Optional[bool] = None


class HealthCheckTCP(BaseModel):
    port: int


class HealthCheckLiveness(BaseModel):
    initial_delay_seconds: Optional[int] = None
    tcp: Optional[HealthCheckTCP] = None


class HealthCheck(BaseModel):
    readiness: Optional[HealthCheckReadiness] = None
    liveness: Optional[HealthCheckLiveness] = None


class LeptonLog(BaseModel):
    save_termination_logs: Optional[bool] = None
    enable_collection: Optional[bool] = None


class LeptonRoutingPolicy(BaseModel):
    enable_header_based_replica_routing: Optional[bool] = None


class LeptonDeploymentUserSpec(BaseModel):
    photon_namespace: Optional[str] = None
    photon_id: Optional[str] = None
    container: Optional[LeptonContainer] = None
    resource_requirement: Optional[ResourceRequirement] = None
    auto_scaler: Optional[AutoScaler] = None
    api_tokens: Optional[List[TokenVar]] = None
    envs: Optional[List[EnvVar]] = None
    mounts: Optional[List[Mount]] = None
    image_pull_secrets: Optional[List[str]] = None
    health: Optional[HealthCheck] = None
    is_pod: Optional[bool] = None
    privileged: Optional[bool] = None
    log: Optional[LeptonLog] = None
    metrics: Optional[LeptonMetrics] = None
    routing_policy: Optional[LeptonRoutingPolicy] = None
    log: Optional[LeptonLog] = None


class LeptonDeploymentState(str, Enum):
    Ready = "Ready"
    NotReady = "Not Ready"
    Starting = "Starting"
    Updating = "Updating"
    Deleting = "Deleting"
    Stopping = "Stopping"
    Stopped = "Stopped"
    Scaling = "Scaling"
    Unknown = "UNK"

    @classmethod
    def _missing_(cls, value):
        if value:
            warnings.warn("You might be using an out of date SDK. consider updating.")
        return cls.Unknown


class DeploymentEndpoint(BaseModel):
    internal_endpoint: str
    external_endpoint: str
    custom_external_endpoint: Optional[List[str]] = None


class AutoscalerCondition(BaseModel):
    status: str
    type_: Optional[str] = Field(default=None, alias="type")
    last_transition_time: Optional[int] = None
    message: Optional[str] = None


class AutoScalerStatus(BaseModel):
    desired_replicas: Optional[int] = None
    last_transition_time: Optional[int] = None
    conditions: Optional[List[AutoscalerCondition]] = None


class LeptonDeploymentStatus(BaseModel):
    state: LeptonDeploymentState
    endpoint: DeploymentEndpoint
    autoscaler_status: Optional[AutoScalerStatus] = None
    with_system_photon: Optional[bool] = None
    is_system: Optional[bool] = None


class LeptonDeployment(BaseModel):
    metadata: Optional[Metadata] = None
    spec: Optional[LeptonDeploymentUserSpec] = None
    status: Optional[LeptonDeploymentStatus] = None
