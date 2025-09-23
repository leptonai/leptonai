from enum import Enum
from pydantic import BaseModel
from typing import Dict, List

from loguru import logger

from leptonai.config import CompatibleRootModel


class ReplicaReadinessReason(str, Enum):
    Ready = "Ready"
    InProgress = "InProgress"
    Deleting = "Deleting"
    Deleted = "Deleted"
    NoCapacity = "NoCapacity"
    ConfigError = "ConfigError"
    SystemError = "SystemError"
    RequireReadinessApproval = "RequireReadinessApproval"
    Queueing = "Queueing"
    Unknown = "Unknown"

    @classmethod
    def _missing_(cls, value):
        logger.trace(f"Unknown value: {value} for ReplicaReadinessReason")
        return cls.Unknown


class ReplicaReadinessIssue(BaseModel):
    reason: ReplicaReadinessReason
    message: str
    creationTimestamp: str


class ReadinessIssue(CompatibleRootModel[Dict[str, List[ReplicaReadinessIssue]]]):
    root: Dict[str, List[ReplicaReadinessIssue]] = {}
