from pydantic import BaseModel
from typing import Dict, List

from leptonai.config import CompatibleRootModel


class ReplicaTermination(BaseModel):
    started_at: int
    finished_at: int
    exit_code: int
    reason: str
    message: str


class DeploymentTerminations(CompatibleRootModel[Dict[str, List[ReplicaTermination]]]):
    root: Dict[str, List[ReplicaTermination]] = {}
