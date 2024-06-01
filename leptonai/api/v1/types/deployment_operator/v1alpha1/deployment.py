from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List


class EnvValue(BaseModel):
    secret_name_ref: str


class EnvVar(BaseModel):
    name: str
    value: Optional[str] = None
    value_from: Optional[EnvValue] = None


class Mount(BaseModel):
    path: str
    mount_path: str


class ContainerPort(BaseModel):
    """
    The port spec of a Lepton Job.
    """

    container_port: int
    protocol: Optional[str] = None
    host_port: Optional[int] = None
    enable_load_balancer: Optional[bool] = None

    @field_validator("container_port")
    def validate_container_port(cls, v):
        if v < 0 or v > 65535:
            raise ValueError("Invalid port number. Port must be between 0 and 65535.")
        return v

    @field_validator("protocol")
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
    resource_affinity: Optional[str] = None
    min_replicas: Optional[int] = None
    max_replicas: Optional[int] = None
    host_network: Optional[bool] = None


class ScaleDown(BaseModel):
    no_traffic_timeout: Optional[int] = None
    not_ready_timeout: Optional[int] = None


class AutoscalerTargetThroughput(BaseModel):
    qpm: Optional[float] = None
    paths: Optional[List[str]] = None
    methods: Optional[List[str]] = None


class AutoScaler(BaseModel):
    scale_down: Optional[ScaleDown] = None
    target_gpu_utilization_percentage: Optional[int] = None
    target_throughput: Optional[AutoscalerTargetThroughput] = None


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
    pull_image_secrets: Optional[List[str]] = None
    health: Optional[HealthCheck] = None
    is_pod: Optional[bool] = None
    privileged: Optional[bool] = None
    log: Optional[LeptonLog] = None
    metrics: Optional[LeptonMetrics] = None
    routing_policy: Optional[LeptonRoutingPolicy] = None


class LeptonDeploymentState(str, Enum):
    Ready = "Ready"
    NotReady = "Not Ready"
    Starting = "Starting"
    Updating = "Updating"
    Deleting = "Deleting"
    Unknown = ""


class DeploymentEndpoint(BaseModel):
    internal_endpoint: str
    external_endpoint: str
    custom_external_endpoint: Optional[List[str]] = None


class AutoscalerCondition(BaseModel):
    status: str
    type_: str = Field(..., alias="type")
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
