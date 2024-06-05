from enum import Enum
from pydantic import BaseModel, RootModel
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
    reason: ReplicaReadinessReason
    message: str
    creationTimestamp: str


class ReadinessIssue(RootModel[Dict[str, List[ReplicaReadinessIssue]]]):
    root: Dict[str, List[ReplicaReadinessIssue]] = {}
