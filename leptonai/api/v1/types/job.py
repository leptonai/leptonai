import warnings
from enum import Enum
from pydantic import BaseModel, field_validator
from typing import Optional, List, Any

from .affinity import LeptonResourceAffinity
from .common import Metadata
from .deployment import (
    LeptonContainer,
    LeptonMetrics,
    EnvVar,
    Mount,
    LeptonLog,
    QueueConfig,
    ReservationConfig,
)


class LeptonJobUserSpec(BaseModel):
    """
    The desired state of a Lepton Job.
    """

    resource_shape: Optional[str] = None
    affinity: Optional[LeptonResourceAffinity] = None
    container: LeptonContainer = LeptonContainer()
    shared_memory_size: Optional[int] = None
    completions: Optional[int] = 1
    parallelism: Optional[int] = 1
    max_failure_retry: Optional[int] = None
    max_job_failure_retry: Optional[int] = None
    envs: Optional[List[EnvVar]] = []
    mounts: Optional[List[Mount]] = []
    image_pull_secrets: Optional[List[str]] = []
    ttl_seconds_after_finished: Optional[int] = None
    intra_job_communication: Optional[bool] = None
    privileged: Optional[bool] = None
    metrics: Optional[LeptonMetrics] = None
    log: Optional[LeptonLog] = None
    queue_config: Optional[QueueConfig] = None
    stopped: Optional[bool] = None
    reservation_config: Optional[ReservationConfig] = None

    # --- ensure backend-required defaults when value is null/absent when using templates ---
    @field_validator("completions", "parallelism", mode="before")
    @classmethod
    def _none_to_one(cls, v: Any) -> int:  # noqa: ANN401
        return 1 if v is None else v

    @field_validator("envs", "mounts", "image_pull_secrets", mode="before")
    @classmethod
    def _none_to_empty(cls, v: Any):  # noqa: ANN401
        return [] if v is None else v


DefaultTTLSecondsAfterFinished: int = 600


class LeptonJobState(str, Enum):
    Starting = "Starting"
    Running = "Running"
    Failed = "Failed"
    Completed = "Completed"
    Stopped = "Stopped"
    Stopping = "Stopping"
    Deleting = "Deleting"
    Deleted = "Deleted"
    Restarting = "Restarting"
    Archived = "Archived"
    Queueing = "Queueing"
    Awaiting = "Awaiting"
    PendingRetry = "PendingRetry"
    Unknown = "UNK"

    @classmethod
    def _missing_(cls, value):
        if value:
            warnings.warn("You might be using an out of date SDK. consider updating.")
        return cls.Unknown


class LeptonJobStatusDetails(BaseModel):
    """
    The current status of a Lepton Job.
    """

    job_name: Optional[str] = None
    state: Optional[LeptonJobState] = None
    ready: Optional[int] = 0
    active: Optional[int] = 0
    failed: Optional[int] = 0
    succeeded: Optional[int] = 0
    creation_time: Optional[int] = None
    completion_time: Optional[int] = None


class LeptonJobStatus(LeptonJobStatusDetails):
    job_history: List[LeptonJobStatusDetails] = []


class LeptonJob(BaseModel):
    metadata: Metadata
    spec: LeptonJobUserSpec = LeptonJobUserSpec()
    status: Optional[LeptonJobStatus] = None
