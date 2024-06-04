from pydantic import BaseModel, RootModel
from typing import Dict, List


class ReplicaTermination(BaseModel):
    started_at: int
    finished_at: int
    exit_code: int
    reason: str
    message: str


class DeploymentTerminations(RootModel[Dict[str, List[ReplicaTermination]]]):
    root: Dict[str, List[ReplicaTermination]] = {}
