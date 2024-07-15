from enum import Enum
from pydantic import BaseModel
from typing import Optional, List

from .affinity import LeptonResourceAffinity
from .common import Metadata
from .deployment import LeptonContainer, LeptonMetrics, EnvVar, Mount


class LeptonJobUserSpec(BaseModel):
    """
    The desired state of a Lepton Job.
    """

    resource_shape: Optional[str] = None
    affinity: Optional[LeptonResourceAffinity] = None
    container: LeptonContainer = LeptonContainer()
    completions: int = 1
    parallelism: int = 1
    max_failure_retry: Optional[int] = None
    max_job_failure_retry: Optional[int] = None
    envs: List[EnvVar] = []
    mounts: List[Mount] = []
    image_pull_secrets: List[str] = []
    ttl_seconds_after_finished: Optional[int] = None
    intra_job_communication: Optional[bool] = None
    privileged: Optional[bool] = None
    metrics: Optional[LeptonMetrics] = None


DefaultTTLSecondsAfterFinished: int = 600


class LeptonJobState(str, Enum):
    Starting = "Starting"
    Running = "Running"
    Failed = "Failed"
    Completed = "Completed"
    Deleting = "Deleting"
    Restarting = "Restarting"
    Unknown = ""


class LeptonJobStatusDetails(BaseModel):
    """
    The current status of a Lepton Job.
    """

    job_name: Optional[str] = None
    state: LeptonJobState
    ready: int
    active: int
    failed: int
    succeeded: int
    creation_time: Optional[int] = None
    completion_time: Optional[int] = None


class LeptonJobStatus(LeptonJobStatusDetails):
    job_history: List[LeptonJobStatusDetails] = []


class LeptonJob(BaseModel):
    metadata: Metadata
    spec: LeptonJobUserSpec = LeptonJobUserSpec()
    status: Optional[LeptonJobStatus] = None
