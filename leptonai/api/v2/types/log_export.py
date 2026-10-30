from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class LogExportState(str, Enum):
    SUBMITTING = "SUBMITTING"
    SUBMISSION_UNKNOWN = "SUBMISSION_UNKNOWN"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


TERMINAL_LOG_EXPORT_STATES = frozenset({
    LogExportState.COMPLETED,
    LogExportState.FAILED,
    LogExportState.EXPIRED,
})


class LogExportWorkload(BaseModel):
    # Only "job" is accepted for new exports; retained records may carry
    # "deployment" or "devpod".
    kind: str
    id_: str = Field(alias="id")
    uid: str


class LogExportFilters(BaseModel):
    # Empty lists select everything; an empty `replicas` means all replicas.
    replicas: List[str] = []
    containers: List[str] = []
    levels: List[str] = []
    contains: str = ""


class LogExportCreateRequest(BaseModel):
    workload: LogExportWorkload
    # RFC3339 timestamps with an explicit timezone.
    start: str
    end: str
    format: str = "ndjson"
    filters: LogExportFilters = LogExportFilters()


class LogExportProgress(BaseModel):
    percent: Optional[float] = None
    # Decimal string; the server keeps large counts out of float range.
    processed_lines: Optional[str] = None


class LogExportFailure(BaseModel):
    reason: str
    message: str
    retryable: bool = False


class LogExportWarning(BaseModel):
    code: str
    message: str


class LogExport(BaseModel):
    id_: str = Field(alias="id")
    state: LogExportState
    workload: LogExportWorkload
    start: str
    end: str
    format: str
    filters: LogExportFilters
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    expires_at: Optional[str] = None
    idempotency_retained_until: Optional[str] = None
    progress: Optional[LogExportProgress] = None
    size_bytes: Optional[str] = None
    failure: Optional[LogExportFailure] = None
    status_observed_at: Optional[str] = None
    status_stale: bool = False
    warnings: List[LogExportWarning] = []
    status_url: Optional[str] = None
    download_url: Optional[str] = None
