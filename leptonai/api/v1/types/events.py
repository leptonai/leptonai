# todo
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class LeptonEvent(BaseModel):
    type_: str = Field(..., alias="type")
    reason: str
    regarding: Optional[Dict[str, Any]] = None  # k8s corev1.ObjectReference
    count: int
    last_observed_time: datetime
