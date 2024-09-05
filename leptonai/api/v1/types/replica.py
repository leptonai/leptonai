from pydantic import BaseModel, Field
from typing import Optional, List

from .common import Metadata


class ReplicaDomain(BaseModel):
    name: str


class Node(BaseModel):
    name: str
    id_: str = Field(..., alias="id")


class ReplicaStatus(BaseModel):
    public_ip: Optional[str] = None
    node: Optional[Node] = None
    domains: Optional[List[ReplicaDomain]] = None


class Replica(BaseModel):
    metadata: Metadata
    # note: id is deprecated. Use metadata.id instead.
    id_: str = Field(..., alias="id")
    status: Optional[ReplicaStatus] = None
