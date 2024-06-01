from pydantic import BaseModel
from typing import Dict, List


class ReplicaTermination(BaseModel):
    started_at: int
    finished_at: int
    exit_code: int
    reason: str
    message: str


class DeploymentTerminations(BaseModel):
    __root__: Dict[str, List[ReplicaTermination]]
