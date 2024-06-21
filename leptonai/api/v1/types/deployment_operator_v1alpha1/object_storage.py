from typing import List

from pydantic import BaseModel


class ObjectStorageMetadata(BaseModel):
    """
    The current status of a Lepton Job.
    """

    key: str
    size: int
    last_modified: int


class ListObjectsResponse(BaseModel):
    items: List[ObjectStorageMetadata]
    prefix: str
    nextContinuationToken: str
