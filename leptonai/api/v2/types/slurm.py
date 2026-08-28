"""Data models for the workspace Slurm APIs.

The Slurm surface is still evolving independently of the regular Lepton job
API.  These models intentionally accept unknown fields so a newer workspace
does not make an older CLI unusable while retaining typed access to the fields
the CLI presents.
"""

from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict
except ImportError:  # Pydantic v1
    ConfigDict = None  # type: ignore


class SlurmBaseModel(BaseModel):
    if hasattr(BaseModel, "model_fields") and ConfigDict is not None:
        model_config = ConfigDict(populate_by_name=True, extra="allow")
    else:

        class Config:
            allow_population_by_field_name = True
            extra = "allow"


class SlurmMetadata(SlurmBaseModel):
    id_: Optional[str] = Field(default=None, alias="id")
    name: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[int] = None
    deleted_at: Optional[int] = None
    created_by: Optional[str] = None
    last_modified_by: Optional[str] = None
    last_modified_at: Optional[int] = None
    owner: Optional[str] = None
    labels: Optional[Dict[str, str]] = None


class SlurmResourceList(SlurmBaseModel):
    cpu: Optional[str] = None
    memory: Optional[str] = None


class SlurmContainerResources(SlurmBaseModel):
    requests: Optional[SlurmResourceList] = None
    limits: Optional[SlurmResourceList] = None


class SlurmDevPodSetConfig(SlurmBaseModel):
    name: Optional[str] = None
    node_group_id: Optional[str] = Field(default=None, alias="nodeGroupId")
    resource_limits: Optional[SlurmResourceList] = Field(
        default=None, alias="resourceLimits"
    )


class SlurmDevPodsConfig(SlurmBaseModel):
    enabled: Optional[bool] = None
    enable_teleport: Optional[bool] = Field(default=None, alias="enableTeleport")
    sets: List[SlurmDevPodSetConfig] = Field(default_factory=list)


class SlurmClusterSpec(SlurmBaseModel):
    worker_cluster_name: Optional[str] = Field(default=None, alias="workerClusterName")
    dev_pods_config: Optional[SlurmDevPodsConfig] = Field(
        default=None, alias="devPodsConfig"
    )


class SlurmClusterStatus(SlurmBaseModel):
    state: Optional[str] = None
    reason: Optional[str] = None
    error: Optional[str] = None
    num_login_nodes: Optional[int] = Field(default=None, alias="numLoginNodes")
    login_node_addresses: List[str] = Field(
        default_factory=list, alias="loginNodeAddresses"
    )
    login_node_names: List[str] = Field(default_factory=list, alias="loginNodeNames")
    teleport_cluster: Optional[str] = Field(default=None, alias="teleportCluster")


class LeptonSlurmCluster(SlurmBaseModel):
    metadata: SlurmMetadata
    spec: Optional[SlurmClusterSpec] = None
    status: Optional[SlurmClusterStatus] = None


class SlurmClusterEvent(SlurmBaseModel):
    timestamp: Optional[str] = None
    type_: Optional[str] = Field(default=None, alias="type")
    cluster_name: Optional[str] = None
    worker_cluster_name: Optional[str] = None
    user: Optional[str] = None
    message: Optional[str] = None


class SlurmClusterMetadata(SlurmBaseModel):
    id_: Optional[str] = Field(default=None, alias="id")
    namespace_id: Optional[str] = None
    cluster_id: Optional[str] = None
    name: Optional[str] = None


class SlurmJobSpec(SlurmBaseModel):
    job_id: Optional[int] = None
    priority: Optional[int] = None
    cpus: Optional[int] = None
    memory_mb: Optional[int] = None
    storage_mb: Optional[int] = None
    gpus: Optional[int] = None
    gpu_memory_mb: Optional[int] = None
    node_count: Optional[int] = None
    account: Optional[str] = None
    command: Optional[str] = None
    dependency: Optional[str] = None
    script: Optional[str] = None
    time_limit_minutes: Optional[int] = None
    working_directory: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    array_job_id: Optional[int] = None
    array_task_id: Optional[int] = None
    num_tasks: Optional[int] = None
    tasks_per_node: Optional[int] = None


class SlurmJobStatus(SlurmBaseModel):
    state: Optional[str] = None
    job_state: Optional[str] = None
    message: Optional[str] = None
    nodes: List[str] = Field(default_factory=list)
    partition: Optional[str] = None
    restart_count: Optional[int] = None
    qos: Optional[str] = None
    failed_node: Optional[str] = None
    exit_code: Optional[int] = None
    kill_request_user: Optional[str] = None
    creation_time: Optional[Union[int, str]] = None
    start_time: Optional[Union[int, str]] = None
    completion_time: Optional[Union[int, str]] = None
    stopped_time: Optional[Union[int, str]] = None
    state_reason: Optional[str] = None


class SlurmJob(SlurmBaseModel):
    metadata: SlurmMetadata
    spec: SlurmJobSpec = Field(default_factory=SlurmJobSpec)
    status: SlurmJobStatus = Field(default_factory=SlurmJobStatus)


class WorkspaceSlurmJob(SlurmJob):
    kind: Optional[str] = None
    slurm_cluster: Optional[SlurmClusterMetadata] = None


class WorkspaceSlurmJobList(SlurmBaseModel):
    page: int = 1
    page_size: int = 0
    total: int = 0
    jobs: List[WorkspaceSlurmJob] = Field(default_factory=list)
    failed_clusters: Dict[str, str] = Field(default_factory=dict)


class SlurmEvent(SlurmBaseModel):
    submit_at: Optional[int] = None
    start_at: Optional[int] = None
    end_at: Optional[int] = None
    nodes: List[str] = Field(default_factory=list)
    state: Optional[str] = None
    return_code: Optional[int] = None
    signal: Optional[int] = None
    signal_name: Optional[str] = None
    cpus: Optional[int] = None
    memory_mb: Optional[int] = None
    storage_mb: Optional[int] = None
    gpus: Optional[int] = None
    gpu_memory_mb: Optional[int] = None


class SlurmStepEvent(SlurmEvent):
    id_: Optional[str] = Field(default=None, alias="id")
    name: Optional[str] = None


class SlurmJobAttempt(SlurmEvent):
    attempt: int
    steps: List[SlurmStepEvent] = Field(default_factory=list)


class SlurmJobEventList(SlurmBaseModel):
    id_: Optional[int] = Field(default=None, alias="id")
    name: Optional[str] = None
    jobs: List[SlurmJobAttempt] = Field(default_factory=list)


class SlurmDevPodSpec(SlurmBaseModel):
    slurm_cluster_name: str = Field(alias="slurmClusterName")
    dev_pod_set_name: Optional[str] = Field(default=None, alias="devPodSetName")
    resource_requests: Optional[SlurmResourceList] = Field(
        default=None, alias="resourceRequests"
    )


class SlurmDevPodStatus(SlurmBaseModel):
    state: Optional[str] = None
    reason: Optional[str] = None
    error: Optional[str] = None
    pod_name: Optional[str] = Field(default=None, alias="podName")
    username: Optional[str] = None
    image_version: Optional[str] = Field(default=None, alias="imageVersion")
    container_resources: Optional[SlurmContainerResources] = Field(
        default=None, alias="containerResources"
    )
    teleport_cluster: Optional[str] = Field(default=None, alias="teleportCluster")
    teleport_node_name: Optional[str] = Field(default=None, alias="teleportNodeName")
    ssh_command: Optional[str] = Field(default=None, alias="sshCommand")


class LeptonSlurmDevPod(SlurmBaseModel):
    metadata: SlurmMetadata
    spec: SlurmDevPodSpec
    status: Optional[SlurmDevPodStatus] = None
