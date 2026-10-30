"""Bulk log export: create a server-side export, poll it, and save the file.

Built on the workspace `/logs/exports` API. The server currently admits new
exports for Jobs only.
"""

import os
import random
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional, Sequence, Tuple

import click
from requests import RequestException

from leptonai.api.v2.log_export import LogExportAPIError
from leptonai.api.v2.types.job import LeptonJobQueryMode
from leptonai.api.v2.types.log_export import (
    LogExport,
    LogExportCreateRequest,
    LogExportFilters,
    LogExportState,
    LogExportWorkload,
    TERMINAL_LOG_EXPORT_STATES,
)

from .log import _preprocess_time
from .util import console

# A single export covers at most this interval (DRS may allow less; the server
# answers `unsupported_range` with the real bound).
DEFAULT_MAX_RANGE = timedelta(hours=24)

POLL_INITIAL_DELAY = 2.0
POLL_MAX_DELAY = 30.0
# Create/download attempts answered with a retryable 429/503 before giving up.
MAX_TRANSIENT_RETRIES = 5
# Errors the server marks as safe to retry with the same request and key.
_RETRYABLE_STATUS = frozenset({429, 503})
_DOWNLOAD_CHUNK = 1 << 16


def _now() -> datetime:
    # Whole seconds, never ahead of the real clock: the API rejects a future end.
    return datetime.now(timezone.utc).replace(microsecond=0)


def _rfc3339(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _to_datetime(value, local_time: bool) -> datetime:
    """Parse a CLI time or epoch (any precision) into an aware UTC datetime."""
    ns = _preprocess_time(value, local_time=local_time, epoch=True)
    return datetime.fromtimestamp(ns / 1_000_000_000, tz=timezone.utc)


def resolve_time_range(
    job, start: Optional[str], end: Optional[str], local_time: bool
) -> Tuple[datetime, datetime]:
    """Return explicit bounds, defaulting to the job's lifetime.

    Defaults: end is the job's completion time (or now while it runs) and start
    is its creation time, clipped to the most recent 24 hours. Explicit values
    are never clipped; the server validates them.
    """
    status = getattr(job, "status", None)
    now = _now()
    if end:
        end_dt = _to_datetime(end, local_time)
    elif status is not None and status.completion_time:
        # Round up so the last log line's second is included.
        end_dt = min(
            _to_datetime(status.completion_time, False).replace(microsecond=0)
            + timedelta(seconds=1),
            now,
        )
    else:
        end_dt = now

    if start:
        start_dt = _to_datetime(start, local_time)
    else:
        created = (
            _to_datetime(status.creation_time, False)
            if status is not None and status.creation_time
            else None
        )
        start_dt = end_dt - DEFAULT_MAX_RANGE
        if created is not None and created > start_dt:
            start_dt = created.replace(microsecond=0)
        else:
            console.print(
                "[yellow]Note[/]: defaulting to the last 24 hours of the job"
                f" ({_rfc3339(start_dt)} to {_rfc3339(end_dt)}). Use --start/--end"
                " to choose another window."
            )

    if end_dt <= start_dt:
        raise click.ClickException(
            f"End time ({_rfc3339(end_dt)}) must be after start time"
            f" ({_rfc3339(start_dt)})."
        )
    return start_dt, end_dt


def require_log_exports_enabled(client, create: bool) -> None:
    """Fail early unless the workspace enables the export operation.

    Mirrors the server's gates: creating needs ``enable_log_exports_create``
    and reading an existing export needs ``enable_log_exports_access``. Only an
    explicit ``true`` counts; older servers omit both flags.
    """
    flag = "enable_log_exports_create" if create else "enable_log_exports_access"
    features = getattr(client.info(), "features", None)
    if getattr(features, flag, None) is True:
        return
    workspace = getattr(client, "workspace_id", None)
    where = f"workspace {workspace}" if workspace else "this workspace"
    if create:
        message = f"Log download is not enabled for {where}."
    else:
        message = f"Downloading existing log exports is not enabled for {where}."
    raise click.ClickException(
        f"{message} Ask your workspace administrator to enable it, or use"
        " `lep job log` / `lep log get` to read logs directly."
    )


def _poll_delay(attempt: int, retry_after: Optional[float]) -> float:
    if retry_after:
        return retry_after
    base = min(POLL_INITIAL_DELAY * (1.5**attempt), POLL_MAX_DELAY)
    return base * random.uniform(0.8, 1.2)


def _resume_hint(export_id: str) -> str:
    return f"lep job log download --export-id {export_id}"


def _describe_error(e: LogExportAPIError) -> str:
    """A user-facing message for a typed `/logs/exports` error."""
    reason = e.reason
    if reason == "unsupported_range":
        parts = [f"The requested time range is not supported ({e})."]
        if e.available_start or e.available_end:
            parts.append(
                f"Available logs: {e.available_start or '?'} to"
                f" {e.available_end or '?'}."
            )
        if e.max_range_seconds:
            parts.append(f"Maximum range: {e.max_range_seconds} seconds.")
        return " ".join(parts)
    if reason == "workload_incarnation_changed":
        return (
            "The job was replaced by a new job with the same ID. Run the command"
            f" again to export the current job's logs ({e})."
        )
    if reason == "idempotency_conflict":
        return f"An export with this key already exists for another request ({e})."
    if reason == "invalid_request":
        return (
            "The server rejected the export request. Check the job ID, time range"
            f" and --replica names (see `lep job replicas`). ({e})"
        )
    if reason == "export_failed":
        return f"The export failed on the server ({e})."
    if reason == "export_expired":
        return f"The export has expired. Create a new one ({e})."
    if e.status_code == 404:
        return f"Log export or job not found ({e})."
    message = str(e)
    if e.request_id:
        message += f" (request ID {e.request_id})"
    return message


def _call_with_retries(fn: Callable):
    """Call `fn`, retrying 429/503 responses the server asks to retry."""
    for attempt in range(MAX_TRANSIENT_RETRIES + 1):
        try:
            return fn()
        except LogExportAPIError as e:
            # An error naming an export means the export exists; the caller
            # tracks it instead of resubmitting.
            if (
                e.status_code not in _RETRYABLE_STATUS
                or e.export_id
                or attempt == MAX_TRANSIENT_RETRIES
            ):
                raise
            delay = _poll_delay(attempt, e.retry_after)
            console.print(
                f"[yellow]Server busy[/] ({e.reason or e.status_code}); retrying in"
                f" {delay:.0f}s..."
            )
            time.sleep(delay)


def create_job_export(
    client,
    job_id: str,
    start: Optional[str],
    end: Optional[str],
    replicas: Sequence[str],
    contains: Optional[str],
    local_time: bool,
) -> str:
    """Create a Job log export and return its ID."""
    # New exports need the live Job: the server does not export archived ones.
    job = client.job.get(job_id, job_query_mode=LeptonJobQueryMode.AliveOnly.value)
    job_uid = job.metadata.uuid
    if not job_uid:
        raise click.ClickException(
            "The server did not return this job's UID, so it does not support log"
            " downloads yet."
        )
    start_dt, end_dt = resolve_time_range(job, start, end, local_time)
    request = LogExportCreateRequest(
        workload=LogExportWorkload(
            kind="job", id=job.metadata.id_ or job_id, uid=job_uid
        ),
        start=_rfc3339(start_dt),
        end=_rfc3339(end_dt),
        filters=LogExportFilters(replicas=list(replicas), contains=contains or ""),
    )
    # One key per command run. Retries below resend the same body under it, so
    # the server never starts a duplicate export.
    key = f"lep-cli-{uuid.uuid4()}"
    try:
        export, _ = _call_with_retries(lambda: client.log_export.create(request, key))
    except LogExportAPIError as e:
        # Submission is in progress or its outcome is unknown: the export exists,
        # so track it rather than submitting again.
        if e.export_id and e.reason in (
            "export_submission_in_progress",
            "export_submission_unknown",
        ):
            console.print(f"[yellow]Note[/]: {e}")
            return e.export_id
        raise click.ClickException(_describe_error(e))
    replica_note = ", ".join(replicas) if replicas else "all replicas"
    console.print(
        f"Created log export [green]{export.id_}[/] for job [green]{job_id}[/]"
        f" ({request.start} to {request.end}, {replica_note})."
    )
    for warning in export.warnings:
        console.print(f"[yellow]Warning[/]: {warning.message}")
    return export.id_


def wait_for_export(client, export_id: str) -> LogExport:
    """Poll until the export reaches a terminal state."""
    attempt = 0
    last_state = None
    warned_stale = False
    while True:
        try:
            export, retry_after = client.log_export.get(export_id)
        except LogExportAPIError as e:
            if e.status_code not in _RETRYABLE_STATUS:
                raise click.ClickException(_describe_error(e))
            export, retry_after = None, e.retry_after
        if export is not None:
            if export.state in TERMINAL_LOG_EXPORT_STATES:
                return export
            if export.status_stale and not warned_stale:
                warned_stale = True
                console.print(
                    "[yellow]Note[/]: the server could not refresh this export's"
                    " status recently; still waiting."
                )
            if export.state != last_state:
                last_state = export.state
                console.print(f"Export state: {export.state.value}")
            if export.state == LogExportState.SUBMISSION_UNKNOWN:
                # Only server-side recovery resolves this, which can take long.
                raise click.ClickException(
                    f"The server could not confirm that export {export_id} was"
                    " submitted. Check again later with"
                    f" `{_resume_hint(export_id)}`."
                )
        time.sleep(_poll_delay(attempt, retry_after))
        attempt += 1


def _default_output(export_id: str) -> str:
    return f"logs-{export_id}.ndjson"


def download_export(
    client,
    export_id: str,
    output: Optional[str],
) -> str:
    """Stream the artifact to `output` and return the saved file's path."""
    path = os.path.abspath(output or _default_output(export_id))
    if os.path.exists(path):
        raise click.ClickException(
            f"{path} already exists. Remove it or choose another --output."
        )

    try:
        response = _call_with_retries(lambda: client.log_export.download(export_id))
    except LogExportAPIError as e:
        raise click.ClickException(_describe_error(e))

    # Write to a temporary sibling so an interrupted transfer never leaves a
    # truncated file under the final name.
    part = f"{path}.part"
    written = 0
    try:
        with response, open(part, "wb") as sink:
            for chunk in response.iter_content(chunk_size=_DOWNLOAD_CHUNK):
                if chunk:
                    sink.write(chunk)
                    written += len(chunk)
    except BaseException as e:
        if os.path.exists(part):
            os.remove(part)
        if not isinstance(e, (RequestException, OSError)):
            raise
        raise click.ClickException(
            f"Download interrupted after {written} bytes: {e}. Retry with"
            f" `{_resume_hint(export_id)}`."
        )
    os.replace(part, path)
    console.print(f"Saved {written} bytes of logs to [green]{path}[/].")
    if written == 0:
        console.print("[yellow]No logs matched the requested range and filters.[/]")
    return path


def run_job_log_download(
    client,
    job_id: Optional[str],
    export_id: Optional[str],
    start: Optional[str],
    end: Optional[str],
    replicas: Sequence[str],
    contains: Optional[str],
    output: Optional[str],
    no_wait: bool,
    local_time: bool,
) -> None:
    if bool(job_id) == bool(export_id):
        raise click.UsageError("Specify exactly one of --id or --export-id.")
    if export_id and (start or end or replicas or contains):
        raise click.UsageError(
            "--start, --end, --replica and --contains apply only to new exports (--id)."
        )

    require_log_exports_enabled(client, create=bool(job_id))
    if job_id:
        export_id = create_job_export(
            client, job_id, start, end, replicas, contains, local_time
        )
    if no_wait:
        console.print(f"Download it later with `{_resume_hint(export_id)}`.")
        return

    try:
        export = wait_for_export(client, export_id)
    except KeyboardInterrupt:
        # The export keeps running server-side; only polling stops.
        console.print(
            "\nStopped waiting. The export continues on the server; resume with"
            f" `{_resume_hint(export_id)}`."
        )
        raise click.exceptions.Exit(130)

    if export.state == LogExportState.FAILED:
        failure = export.failure
        detail = f": {failure.message} ({failure.reason})" if failure else ""
        raise click.ClickException(f"Log export {export_id} failed{detail}.")
    if export.state == LogExportState.EXPIRED:
        raise click.ClickException(
            f"Log export {export_id} has expired. Create a new one with --id."
        )
    if export.status_stale:
        console.print(
            "[yellow]Note[/]: the server could not refresh this export's status"
            " recently."
        )
    download_export(client, export_id, output)
