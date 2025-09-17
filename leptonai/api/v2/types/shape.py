from typing import Optional, List
from pydantic import BaseModel
from leptonai.api.v1.types.common import Metadata


class ShapeSpec(BaseModel):
    # Display name and description
    name: Optional[str] = None
    description: Optional[str] = None

    # Visibility / listing
    listable_in: Optional[List[str]] = None

    # CPU and memory
    cpu: Optional[float] = None
    memory_in_mb: Optional[int] = None
    ephemeral_storage_in_gb: Optional[int] = None
    is_adaptive: Optional[bool] = None

    # Accelerator related
    accelerator_type: Optional[str] = None
    accelerator_num: Optional[float] = None
    accelerator_fraction: Optional[float] = None
    accelerator_memory_in_mb: Optional[int] = None
    accelerator_pass_all: Optional[bool] = None
    node_group_id: Optional[str] = None


class Shape(BaseModel):
    metadata: Metadata
    spec: ShapeSpec
