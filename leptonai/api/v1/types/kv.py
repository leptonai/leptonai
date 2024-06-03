from pydantic import BaseModel
from typing import Optional

from .common import Metadata


class KVStatus(BaseModel):
    redis_url: str


class KV(BaseModel):
    name: Optional[str] = None
    metadata: Metadata
    status: KVStatus
