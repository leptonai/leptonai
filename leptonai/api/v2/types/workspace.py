from pydantic import BaseModel
from typing import Optional


class ResourceShape(BaseModel):
    description: Optional[str] = None
    cpu: Optional[float] = None
    memory_in_mb: Optional[int] = None
    ephemeral_storage_in_gb: Optional[int] = None
    accelerator_type: Optional[str] = None
    accelerator_num: Optional[float] = None
    accelerator_fraction: Optional[float] = None
    accelerator_memory_in_mb: Optional[int] = None
