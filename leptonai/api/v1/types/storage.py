from pydantic import BaseModel
from typing import Optional

from .common import Metadata


class FileSystemStatus(BaseModel):
    """
    The current status of a FileSystem.
    """

    total_usage_bytes: Optional[int] = None


class FileSystem(BaseModel):
    metadata: Optional[Metadata] = None
    status: Optional[FileSystemStatus] = None


class DirInfo(BaseModel):
    type: Optional[str] = None
    name: Optional[str] = None
    path: Optional[str] = None
