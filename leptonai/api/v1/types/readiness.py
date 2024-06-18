from enum import Enum
from pydantic import BaseModel
from typing import Dict, List

from leptonai.config import CompatibleRootModel


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


class ReadinessIssue(CompatibleRootModel[Dict[str, List[ReplicaReadinessIssue]]]):
    root: Dict[str, List[ReplicaReadinessIssue]] = {}
