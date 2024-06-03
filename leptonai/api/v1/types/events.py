# todo
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class LeptonEvent(BaseModel):
    type_: str = Field(..., alias="type")
    reason: str
    regarding: Optional[Dict[str, Any]] = None  # k8s corev1.ObjectReference
    count: int
    last_observed_time: int
