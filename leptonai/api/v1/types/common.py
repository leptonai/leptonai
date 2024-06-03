from pydantic import BaseModel, Field
from typing import Optional


class MetadataV1(BaseModel):
    """
    The deprecated MetadataV1 class, corresponding to httptypes.MetadataV1.

    This class is deprecated and should not be used. For newer versions of
    the metadata class, use the Metadata class.
    """

    id: Optional[str] = None
    created_at: Optional[int] = None
    version: Optional[int] = None


class Metadata(BaseModel):
    """
    The metadata field, corresponding to httptypes.MetadataV2.
    """

    id: Optional[str] = None
    name: Optional[str] = None
    created_at: Optional[int] = None
    version: Optional[int] = None
    created_by: Optional[str] = None
    last_modified_by: Optional[str] = None
