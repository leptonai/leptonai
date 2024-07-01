from typing import List

from pydantic import BaseModel


class ObjectStorageMetadata(BaseModel):
    """
    The metadata for a stored object.
    """

    key: str
    size: int
    last_modified: int


class ListObjectsResponse(BaseModel):
    items: List[ObjectStorageMetadata]
    prefix: str
    nextContinuationToken: str
