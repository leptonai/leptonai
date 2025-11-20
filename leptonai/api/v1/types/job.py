from enum import Enum
from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional, List, Any
from loguru import logger

from .affinity import LeptonResourceAffinity
from .common import Metadata, LeptonUserSecurityContext
from .deployment import (
    LeptonContainer,
    LeptonMetrics,
    EnvVar,
    Mount,
    LeptonLog,
    QueueConfig,
    ReservationConfig,
)

DefaultTTLSecondsAfterFinished: int = 600


class LeptonJobTimeSchedule(BaseModel):
    """Schedule for job execution time."""

    start_at: Optional[int] = None  # StartAt is unix time in seconds


class LeptonJobSegmentConfig(BaseModel):
    """Segment configuration for segmented job execution."""

    count_per_segment: int


class LeptonJobQueryMode(str, Enum):
    AliveOnly = "alive_only"
    ArchiveOnly = "archive_only"
    AliveAndArchive = "alive_and_archive"


class LeptonJobUserSpec(BaseModel):
    """
    The desired state of a Lepton Job.
    """

    model_config = ConfigDict(validate_assignment=True)

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
    ttl_seconds_after_finished: Optional[int] = DefaultTTLSecondsAfterFinished
    intra_job_communication: Optional[bool] = None
    user_security_context: Optional[LeptonUserSecurityContext] = None
    metrics: Optional[LeptonMetrics] = None
    log: Optional[LeptonLog] = None
    queue_config: Optional[QueueConfig] = None
    stopped: Optional[bool] = None
    reservation_config: Optional[ReservationConfig] = None
    time_schedule: Optional[LeptonJobTimeSchedule] = None
    segment_config: Optional[LeptonJobSegmentConfig] = None

    # --- ensure backend-required defaults when value is null/absent when using templates ---
    @field_validator("completions", "parallelism", mode="before")
    @classmethod
    def _none_to_one(cls, v: Any) -> int:  # noqa: ANN401
        return 1 if v is None else v

    @field_validator("envs", "mounts", "image_pull_secrets", mode="before")
    @classmethod
    def _none_to_empty(cls, v: Any):  # noqa: ANN401
        return [] if v is None else v

    @field_validator(
        "ttl_seconds_after_finished", "max_failure_retry", "max_job_failure_retry"
    )
    @classmethod
    def _validate_optional_non_negative(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if v < 0:
            raise ValueError("value must be >= 0")
        return v


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
        logger.trace(f"Unknown value: {value} for LeptonJobState")
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
