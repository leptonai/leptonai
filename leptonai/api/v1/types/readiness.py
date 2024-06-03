from enum import Enum
from pydantic import BaseModel
from typing import Dict, List


class ReplicaReadinessReason(str, Enum):
    Ready = "Ready"
    InProgress = "InProgress"
    Deleting = "Deleting"
    Deleted = "Deleted"
    NoCapacity = "NoCapacity"
    ConfigError = "ConfigError"
    SystemError = "SystemError"
    Unknown = "Unknown"
    RequireReadinessApproval = "RequireReadinessApproval"


class ReplicaReadinessIssue(BaseModel):
    reason = ReplicaReadinessReason
    message = str
    creationTimestamp = int


class ReadinessIssue(BaseModel):
    __root__: Dict[str, List[ReplicaReadinessIssue]]
