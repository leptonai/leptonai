from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


class MetadataV1(BaseModel):
    """
    The deprecated MetadataV1 class, corresponding to httptypes.MetadataV1.

    This class is deprecated and should not be used. For newer versions of
    the metadata class, use the Metadata class.
    """

    id_: Optional[str] = Field(None, alias="id")
    created_at: Optional[int] = None
    version: Optional[int] = None


class LeptonVisibility(str, Enum):
    """
    The visibility of a Lepton resource.
    """

    PUBLIC = "public"
    PRIVATE = "private"


class Metadata(BaseModel):
    """
    The metadata field, corresponding to httptypes.MetadataV2.
    """

    id_: Optional[str] = Field(default=None, alias="id")
    name: Optional[str] = None
    created_at: Optional[int] = None
    version: Optional[int] = None
    created_by: Optional[str] = None
    last_modified_by: Optional[str] = None
    semantic_version: Optional[str] = None

    # Implementation note: this is the inlined LeptonMetadata in the backend
    owner: Optional[str] = None
    last_modified_at: Optional[int] = None
    visibility: Optional[LeptonVisibility] = None
    replica_version: Optional[str] = None


class SecretItem(BaseModel):
    name: str
    value: str
