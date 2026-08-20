from typing import List, Optional

from pydantic import BaseModel, Field


class StoragePermission(BaseModel):
    path_prefix: str
    allowed_users: List[str] = Field(default_factory=list)
    subfolder_policy: str = ""
    nodegroup_id: Optional[str] = None
