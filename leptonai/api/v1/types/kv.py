from pydantic import BaseModel
from typing import Optional, List

from .common import Metadata


class ListKeysResponse(BaseModel):
    cursor: Optional[int] = None
    keys: List[str]


class KVStatus(BaseModel):
    redis_url: str


class KV(BaseModel):
    name: Optional[str] = None
    metadata: Metadata
    status: KVStatus
