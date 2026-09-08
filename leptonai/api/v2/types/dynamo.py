"""
Types for Dynamo graph deployments: multi-service inference graphs served by
NVIDIA Dynamo (vLLM, SGLang, or TensorRT-LLM backends).

The spec models mirror the ``LeptonDynamoGraphDeployment`` CRD user spec
(``deployment-operator/api/v1alpha1/leptondynamographdeployment_types.go``);
the response models mirror ``api-server/httpapi/dynamo/types.go``. Field names
match the JSON wire format exactly.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from loguru import logger
from pydantic import BaseModel, Field

from .affinity import LeptonResourceAffinity
from .auth import AuthConfig
from .common import Metadata
from .deployment import EnvVar, LeptonRoutingPolicy, Mount
from .ingress import LoadBalanceConfig
from .readiness import ReplicaReadinessReason


class DynamoBackendFramework(str, Enum):
    VLLM = "vllm"
    SGLANG = "sglang"
    TRTLLM = "trtllm"


class DynamoServingMode(str, Enum):
    AGGREGATED = "aggregated"
    DISAGGREGATED = "disaggregated"


class DynamoComponentType(str, Enum):
    FRONTEND = "frontend"
    WORKER = "worker"


# Service names used by the dashboard. The API accepts arbitrary service keys,
# but only these four have default images and commands in the CLI defaults
# registry (see leptonai.api.v2.dynamo_spec).
DYNAMO_FRONTEND_SERVICE = "frontend"
DYNAMO_SERVICE_NAMES = ("frontend", "worker", "prefill-worker", "decode-worker")

# Pod label the dashboard stamps on prefill/decode workers.
DYNAMO_WORKER_ROLE_LABEL_KEY = "lepton.ai/dynamo-worker-role"
DYNAMO_WORKER_ROLE_BY_SERVICE = {
    "prefill-worker": "prefill",
    "decode-worker": "decode",
}


# ---------------------------------------------------------------------------
# Spec
# ---------------------------------------------------------------------------


class DynamoMultinodeSpec(BaseModel):
    """Multinode configuration. ``node_count`` must be >= 2 (worker services only)."""

    node_count: Optional[int] = None


class DynamoMainContainerSpec(BaseModel):
    image: Optional[str] = None
    working_dir: Optional[str] = None
    command: Optional[List[str]] = None


class DynamoExtraPodSpec(BaseModel):
    main_container: Optional[DynamoMainContainerSpec] = None
    image_pull_secrets: Optional[List[str]] = None
    node_selector: Optional[Dict[str, str]] = None
    termination_grace_period_seconds: Optional[int] = None


class DynamoExtraPodMetadata(BaseModel):
    annotations: Optional[Dict[str, str]] = None
    labels: Optional[Dict[str, str]] = None


class LeptonDynamoServiceSpec(BaseModel):
    """
    One service (frontend or worker) inside a Dynamo graph deployment.

    The resource requirement fields are inlined in the CRD
    (``LeptonDeploymentResourceRequirement``), so they sit at the top level of
    the service rather than under ``resource_requirement`` as endpoints do.
    """

    component_type: Optional[str] = None
    envs: Optional[List[EnvVar]] = None
    env_from_secret: Optional[str] = None
    mounts: Optional[List[Mount]] = None
    multinode: Optional[DynamoMultinodeSpec] = None

    # Inlined LeptonDeploymentResourceRequirement.
    resource_shape: Optional[str] = None
    cpu: Optional[float] = None
    memory: Optional[int] = None
    ephemeral_storage_in_gb: Optional[int] = None
    accelerator_type: Optional[str] = None
    accelerator_num: Optional[float] = None
    accelerator_fraction: Optional[float] = None
    accelerator_memory: Optional[int] = None
    accelerator_pass_all: Optional[bool] = None
    shared_memory_size: Optional[int] = None
    # Deprecated upstream; kept only so server responses round-trip.
    resource_affinity: Optional[str] = None
    affinity: Optional[LeptonResourceAffinity] = None
    min_replicas: Optional[int] = None
    # Autoscaling is not supported yet: the server forces max_replicas == min_replicas.
    max_replicas: Optional[int] = None
    host_network: Optional[bool] = None
    is_adaptive: Optional[bool] = None

    extra_pod_metadata: Optional[DynamoExtraPodMetadata] = None
    extra_pod_spec: Optional[DynamoExtraPodSpec] = None


class LeptonDynamoGraphDeploymentUserSpec(BaseModel):
    """User-facing spec of a Dynamo graph deployment."""

    display_name: Optional[str] = None
    # Must stay empty for Dynamo 1.3.1 (the server rejects any non-empty value).
    # Present only so that server responses round-trip through the model.
    dynamo_namespace: Optional[str] = None
    dynamo_version: Optional[str] = None
    backend_framework: Optional[str] = None
    ingress_enabled: Optional[bool] = None
    # Global environment variables applied to every service.
    envs: Optional[List[EnvVar]] = None
    services: Optional[Dict[str, LeptonDynamoServiceSpec]] = None
    load_balance_config: Optional[Union[LoadBalanceConfig, Dict[str, Any]]] = None
    routing_policy: Optional[LeptonRoutingPolicy] = None
    auth_config: Optional[AuthConfig] = None
    # Valid range 300..3600; the server defaults to 300 when unset.
    ingress_timeout_seconds: Optional[int] = None


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


class LeptonDynamoGraphDeploymentState(str, Enum):
    """Aggregated deployment-level state (LDGD states in the CRD)."""

    Ready = "Ready"
    Starting = "Starting"
    Updating = "Updating"
    NotReady = "Not Ready"
    Deleting = "Deleting"
    # Offered by the dashboard's status filter; kept so they never render as UNK.
    Scaling = "Scaling"
    Stopping = "Stopping"
    Stopped = "Stopped"
    # Backend represents the unknown state as an empty string ("").
    Unknown = "UNK"

    @classmethod
    def _missing_(cls, value):
        logger.trace(f"Unknown value: {value} for LeptonDynamoGraphDeploymentState")
        return cls.Unknown


class LeptonDynamoServiceState(str, Enum):
    """Per-service state."""

    Ready = "Ready"
    Starting = "Starting"
    Updating = "Updating"
    Scaling = "Scaling"
    Restarting = "Restarting"
    NotReady = "Not Ready"
    Unknown = "UNK"

    @classmethod
    def _missing_(cls, value):
        logger.trace(f"Unknown value: {value} for LeptonDynamoServiceState")
        return cls.Unknown


class DynamoK8sCondition(BaseModel):
    """k8s ``metav1.Condition`` as serialized in the deployment status."""

    type_: Optional[str] = Field(default=None, alias="type")
    status: Optional[str] = None
    reason: Optional[str] = None
    message: Optional[str] = None
    last_transition_time: Optional[str] = Field(
        default=None, alias="lastTransitionTime"
    )
    observed_generation: Optional[int] = Field(default=None, alias="observedGeneration")


class DynamoDeploymentEndpoint(BaseModel):
    internal_endpoint: Optional[str] = None
    external_endpoint: Optional[str] = None
    custom_external_endpoint: Optional[List[str]] = None


class LeptonDynamoServiceStatus(BaseModel):
    state: Optional[LeptonDynamoServiceState] = None
    ready_replicas: Optional[int] = None
    desired_replicas: Optional[int] = None
    last_ready_replicas: Optional[int] = None


class LeptonDynamoGraphDeploymentStatus(BaseModel):
    state: Optional[LeptonDynamoGraphDeploymentState] = None
    conditions: Optional[List[DynamoK8sCondition]] = None
    observed_generation: Optional[int] = None
    services: Optional[Dict[str, LeptonDynamoServiceStatus]] = None
    endpoint: Optional[DynamoDeploymentEndpoint] = None
    default_lepton_ingress: Optional[str] = None


class LeptonDynamoGraphDeployment(BaseModel):
    metadata: Optional[Metadata] = None
    spec: Optional[LeptonDynamoGraphDeploymentUserSpec] = None
    status: Optional[LeptonDynamoGraphDeploymentStatus] = None


# ---------------------------------------------------------------------------
# Sub-resource responses (api-server/httpapi/dynamo/types.go)
# ---------------------------------------------------------------------------


class DynamoServiceInfo(BaseModel):
    """One entry of ``GET .../services``."""

    component_type: Optional[str] = None
    min_replicas: Optional[int] = None
    max_replicas: Optional[int] = None
    desired_replicas: Optional[int] = None
    ready_replicas: Optional[int] = None
    total_pods: Optional[int] = None
    is_multinode: Optional[bool] = None
    node_count: Optional[int] = None


class DynamoServicesResponse(BaseModel):
    services: Dict[str, DynamoServiceInfo] = {}


class DynamoServiceReplicaStatus(BaseModel):
    desired: Optional[int] = None
    ready: Optional[int] = None
    running: Optional[int] = None
    total_pods: Optional[int] = None


class DynamoServiceCondition(BaseModel):
    type_: Optional[str] = Field(default=None, alias="type")
    status: Optional[str] = None
    reason: Optional[str] = None
    message: Optional[str] = None
    last_transition_time: Optional[int] = None


class DynamoReplicaErrorEvent(BaseModel):
    """``http.ReplicaErrorEvent`` surfaced in a service status."""

    name: Optional[str] = None
    reason: Optional[str] = None
    message: Optional[str] = None
    node_name: Optional[str] = None
    node_group_id: Optional[str] = None
    timestamp: Optional[int] = None


class DynamoServiceStatus(BaseModel):
    state: Optional[str] = None
    phase: Optional[str] = None
    health: Optional[str] = None
    replicas: Optional[DynamoServiceReplicaStatus] = None
    conditions: Optional[List[DynamoServiceCondition]] = None
    last_replica_error_events: Optional[List[DynamoReplicaErrorEvent]] = None
    last_updated: Optional[int] = None
    uptime: Optional[int] = None


class DynamoServiceResponse(BaseModel):
    """``GET .../services/:service``."""

    name: Optional[str] = None
    component_type: Optional[str] = None
    resource_shape: Optional[str] = None
    min_replicas: Optional[int] = None
    max_replicas: Optional[int] = None
    desired_replicas: Optional[int] = None
    ready_replicas: Optional[int] = None
    running_replicas: Optional[int] = None
    total_pods: Optional[int] = None
    is_multinode: Optional[bool] = None
    node_count: Optional[int] = None
    spec: Optional[LeptonDynamoServiceSpec] = None
    status: Optional[DynamoServiceStatus] = None


class DynamoReplicaNode(BaseModel):
    name: Optional[str] = None
    id_: Optional[str] = Field(default=None, alias="id")
    node_group_id: Optional[str] = None


class DynamoReplicaDomain(BaseModel):
    name: Optional[str] = None


class DynamoReplicaReadinessIssue(BaseModel):
    reason: ReplicaReadinessReason = ReplicaReadinessReason.Unknown
    message: Optional[str] = None
    creationTimestamp: Optional[str] = None


class DynamoReplicaStatus(BaseModel):
    cpu: Optional[float] = None
    memory_in_mb: Optional[float] = None
    ephemeral_storage_in_gb: Optional[float] = None
    gpus: Optional[float] = None
    public_ip: Optional[str] = None
    local_ip: Optional[str] = None
    node: Optional[DynamoReplicaNode] = None
    domains: Optional[List[DynamoReplicaDomain]] = None
    readiness_issue: Optional[DynamoReplicaReadinessIssue] = None
    last_termination: Optional[Dict[str, Any]] = None
    container_status: Optional[Dict[str, Any]] = None


class DynamoReplica(BaseModel):
    """A pod of one Dynamo service."""

    metadata: Metadata
    # Deprecated upstream; use metadata.id_ instead.
    id_: Optional[str] = Field(default=None, alias="id")
    status: Optional[DynamoReplicaStatus] = None


class DynamoServiceReplicasResponse(BaseModel):
    """``GET .../services/:service/replicas``."""

    service: Optional[str] = None
    replicas: List[DynamoReplica] = []
    is_multinode: Optional[bool] = None
    node_count: Optional[int] = None


class DynamoReplicaLogResponse(BaseModel):
    """One-shot log payload of ``GET .../replicas/:rid/log``."""

    deployment: Optional[str] = None
    service: Optional[str] = None
    replica: Optional[str] = None
    logs: Optional[str] = None


class DynamoReplicaDeleteResponse(BaseModel):
    message: Optional[str] = None
    replica: Optional[str] = None
    service: Optional[str] = None


class DynamoServiceRestartResponse(BaseModel):
    message: Optional[str] = None
    service: Optional[str] = None
    deleted_pods: Optional[List[str]] = None


class DynamoMonitoringStatusResponse(BaseModel):
    """``GET .../monitoring/status``; ``overall_health`` is healthy|degraded|unhealthy."""

    overall_health: Optional[str] = None
    total_services: Optional[int] = None
    healthy_services: Optional[int] = None
    services: Optional[Dict[str, str]] = None


class DynamoHistoryItem(BaseModel):
    timestamp: Optional[int] = None
    operation: Optional[str] = None
    description: Optional[str] = None
