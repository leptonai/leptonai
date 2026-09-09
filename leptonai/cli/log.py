import contextlib
import heapq
import itertools
import random
import re
import sys
import threading
import traceback
from dataclasses import dataclass
from typing import Callable, List, NoReturn, Optional, Tuple

from loguru import logger
from .util import _get_newest_job_by_name
from .util import click_group, console
from .util import resolve_save_path, PathResolutionError

from ..api.v2.client import APIClient
from ..api.v2.log import LogAPIError

import json
import click
import time

from datetime import datetime, timedelta, timezone
from rich.progress import Progress
from concurrent.futures import (
    FIRST_COMPLETED,
    ThreadPoolExecutor,
    wait,
)

str_time_format = "%Y-%m-%d %H:%M:%S.%f"
str_date_format = "%Y-%m-%d"

_supported_formats_log = """
        Please note that all times must be in UTC.
        Keywords such as “now,” “today,” and “yesterday” will be interpreted as UTC timestamps.
        For example, “now” corresponds to datetime.now(timezone.utc).

        - now
          Example: now (indicates the current time in UTC)

        - Full Date and Time:
          Format: YYYY/MM/DD HH:MM:SS.123456
          Example: 2024/12/25 13:10:01.123456

          Alternate Format: YYYY-MM-DD HH:MM:SS.123456
          Example: 2024-12-25 13:10:01.123456

        - today or td:
          Example Variations:
          today (defaults to midnight of the current day in UTC)
          today 01 (1 AM of the current day)
          today 01:10 (1:10 AM of the current day)
          today 01:10:01 (1:10:01 AM of the current day)
          today 01:10:01.123456 (1:10:01 AM with microseconds precision)

        - yesterday or yd:
          Example Variations:
          yesterday (defaults to midnight of the previous day in UTC)
          yesterday 13 (1 PM of the previous day)
          yesterday 13:10 (1:10 PM of the previous day)
          yesterday 13:10:05 (1:10:05 PM of the previous day)
          yesterday 13:10:01.123456 (1:10:01 PM with microseconds precision on the previous day)
        
        - Note for jobs:
          - When using --job/-j or --job-name/-jn, you can omit --start/--end.
          - We'll use the job's creation_time and completion_time (if available).
          - If the job hasn't completed, end defaults to 'now'.
        """


def _preprocess_time(
    input_time, local_time=False, epoch=False, supported_formats=_supported_formats_log
):
    """Parse user time input into a timezone-aware datetime (UTC by default) or a
    nanosecond epoch timestamp.

    Supported inputs:
    - Keywords (can be combined with time of day):
      - now
      - today / td
      - yesterday / yd
      - tomorrow / tm
      Examples: "today", "today 01", "today 01:10", "today 01:10:01.123456"

    - Standard formats (microseconds optional):
      - YYYY-MM-DD HH:MM:SS[.ffffff]
      - YYYY/MM/DD HH:MM:SS[.ffffff]

    Behavior:
    - Parsed as UTC by default; if local_time=True, parse/convert in local timezone.
    - If epoch=True, return a nanosecond timestamp; otherwise return a datetime.
    - If epoch=True and input starts with "search_before,", subtract an extra 2 days
      from the resulting timestamp (used by historical search windows).

    On invalid formats, prints supported formats and exits the program.
    """
    if epoch:
        search_time_offset_ns = 0
        if isinstance(input_time, str) and input_time.startswith("search_before,"):
            input_time = input_time[len("search_before,") :]
            console.print(input_time)
            search_time_offset_ns = -2 * 24 * 60 * 60 * 1_000_000_000

        if isinstance(input_time, (int, float)) or (
            isinstance(input_time, str) and re.fullmatch(r"-?\d+", input_time.strip())
        ):
            epoch_int = int(input_time)
            abs_val = abs(epoch_int)
            if abs_val < 100_000_000_000:  # seconds
                ns = epoch_int * 1_000_000_000
            elif abs_val < 100_000_000_000_000:  # milliseconds
                ns = epoch_int * 1_000_000
            elif abs_val < 100_000_000_000_000_000:  # microseconds
                ns = epoch_int * 1_000
            else:  # nanoseconds
                ns = epoch_int
            return ns + search_time_offset_ns

    now = datetime.now(timezone.utc) if not local_time else datetime.now().astimezone()

    input_time = input_time.replace("/", "-")

    input_time = re.sub(
        r"(\.\d{1,5})(?!\d)", lambda m: m.group(1).ljust(7, "0"), input_time
    )

    input_time = input_time.lower().replace("today", now.strftime(str_date_format), 1)
    input_time = input_time.lower().replace("td", now.strftime(str_date_format), 1)
    input_time = input_time.lower().replace(
        "yesterday", (now - timedelta(days=1)).strftime(str_date_format), 1
    )
    input_time = input_time.lower().replace(
        "yd", (now - timedelta(days=1)).strftime(str_date_format), 1
    )
    input_time = input_time.lower().replace(
        "tomorrow", (now + timedelta(days=1)).strftime(str_date_format), 1
    )
    input_time = input_time.lower().replace(
        "tm", (now + timedelta(days=1)).strftime(str_date_format), 1
    )
    if input_time.lower() == "now":
        input_time = now.strftime(str_time_format)

    # Parse the time and ensure it uses the utc timezone
    try:
        parsed_time = datetime.fromisoformat(input_time)
        if not local_time:
            parsed_time = parsed_time.replace(tzinfo=timezone.utc)

    except ValueError:
        console.print(
            "[red]Invalid time format. Supported formats are:[/]\n" + supported_formats
        )
        sys.exit(1)

    if epoch:
        return int(parsed_time.timestamp() * 1_000_000_000) + search_time_offset_ns

    return parsed_time


def _epoch_to_time_str(nanoseconds, local_time=False):
    """Convert a nanosecond timestamp to a formatted time string.

    Args:
        nanoseconds (int or str): Timestamp in nanoseconds since epoch
        local_time (bool): If True, convert to local timezone; if False, use UTC

    Returns:
        str: Formatted time string in format 'YYYY-MM-DD HH:MM:SS.ffffff'

    Examples:
        >>> _epoch_to_time_str(1710928800000000000)  # UTC
        '2024-03-20 10:00:00.000000'
        >>> _epoch_to_time_str(1710928800000000000, local_time=True)  # Local time
        '2024-03-20 03:00:00.000000'  # Example for Los Angeles (UTC-7)
    """
    if isinstance(nanoseconds, str):
        nanoseconds = int(nanoseconds)

    seconds = nanoseconds / 1e9
    if local_time:
        time_obj = datetime.fromtimestamp(seconds)
    else:
        time_obj = datetime.fromtimestamp(seconds, tz=timezone.utc)

    return time_obj.strftime(str_time_format)


def safe_load_json(string):
    try:
        return json.loads(string)
    except json.JSONDecodeError:
        return string


########################################################################
# Adaptive parallel log retrieval (no-`--limit` path)
#
# Work-queue / bisection scheduler: workers pull [start, end) intervals,
# fetch forward, and only bisect the unscanned remainder of an interval
# when a fetch saturates the per-request limit. See
# docs/log-adaptive-fetch/spec.md for the full design.
########################################################################

# Per-request page size for the adaptive scheduler's forward fetches --
# matches the LEGACY `--limit` path's existing request cap.
_ADAPTIVE_PAGE_LIMIT = 10000

# Maximum number of failed time ranges listed inline in the saved --path
# file's footer. The full untruncated list still goes to the trace log.
_FAILED_RANGES_FILE_CAP = 5

# Per-request timeout for the adaptive scheduler's fetches, shorter than the
# client's normal 120s default. Bounds how long a sink-failure-triggered
# shutdown can be stalled waiting for a worker mid-HTTP-request.
_ADAPTIVE_FETCH_TIMEOUT_SEC = 30

# Retry policy for `_fetch_log_unit`'s per-unit fetch: up to 5 attempts,
# exponential backoff starting at 1.0s (1/2/4/8s schedule), capped at 60s --
# also the cap applied to a 429 response's `Retry-After` value.
_ADAPTIVE_RETRY_MAX_ATTEMPTS = 5
_ADAPTIVE_RETRY_BASE_DELAY_SEC = 1.0
_ADAPTIVE_RETRY_AFTER_CAP_SEC = 60.0


@dataclass(frozen=True)
class LogEntry:
    """A single fetched log record, canonicalized for hashing/equality.

    `stream_labels`/`metadata` are sorted tuples (rather than dicts) so
    `LogEntry` is hashable and has well-defined equality, which the
    commit-watermark buffer's flush-time de-duplication relies on.
    """

    stream_labels: Tuple[Tuple[str, str], ...]
    timestamp_ns: int
    line: str
    metadata: Tuple[Tuple[str, str], ...] = ()


@dataclass(frozen=True)
class WorkUnit:
    """One schedulable half-open interval `[start, end)` (ns epoch).

    `seq_id` is assigned in submission order (parent before its children,
    left child before right child) from a counter allocated only by the
    scheduler's owning thread, and doubles as the buffer's tie-break key.
    """

    seq_id: int
    start: int
    end: int

    def __lt__(self, other: "WorkUnit") -> bool:
        """Total order by `(start, seq_id)` for use as a `heapq` key.

        Hand-written rather than `@dataclass(order=True)`, which would
        compare fields in declaration order (`seq_id` before `start`) and
        require reordering the fields, breaking existing positional
        `WorkUnit(seq_id, start, end)` construction call sites.
        """
        return (self.start, self.seq_id) < (other.start, other.seq_id)


@dataclass(frozen=True)
class FetchUnitResult:
    """Outcome of one single-unit forward fetch, produced by `_fetch_log_unit`."""

    entries: List[LogEntry]
    saturated: bool
    min_ts: Optional[int]
    max_ts: Optional[int]
    failed: bool


class _MalformedLogResponseError(Exception):
    """Raised when a 2xx `/logs` response body doesn't match the expected
    `data.result[].{stream,values}` shape, or a parsed entry's
    `timestamp_ns` falls outside the requested `[start, end)`. Always caught
    by `_fetch_log_unit`'s retry loop -- never reaches the scheduler
    directly.
    """


class _WatermarkRegressionError(Exception):
    """Raised when a recomputed commit watermark is less than
    `self.last_watermark` -- a handled control-flow branch instead of a bare
    `assert`, so a backend bug funnels into the same fail-fast shutdown as a
    sink failure instead of an uncaught traceback.
    """


class _RateLimitSignal:
    """Thread-safe shared 429 signal.

    Workers call `signal(cooldown_seconds)` from `_fetch_log_unit` when they
    observe a 429; the scheduler's owning thread calls `active()` from
    `_submit_ready` before submitting new work.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._until = 0.0  # time.monotonic() deadline; 0.0 == inactive

    def signal(self, cooldown_seconds: float) -> None:
        with self._lock:
            self._until = max(self._until, time.monotonic() + cooldown_seconds)

    def active(self) -> bool:
        with self._lock:
            return time.monotonic() < self._until


# A sink consumes entries in chronological order, as released by the commit
# watermark; it must propagate any write failure by raising.
EmitFn = Callable[[List[LogEntry]], None]


_HASHABLE_SCALAR_TYPES = (str, int, float, bool, type(None))


def _validate_positive_int_limit(limit: int) -> None:
    """Raise `ValueError` unless `limit` is a positive `int`.

    `limit` is an internal contract (always `_ADAPTIVE_PAGE_LIMIT` in
    production), not backend data -- a violation is our own bug, so it's a
    plain precondition failure, not `_MalformedLogResponseError`, and is
    checked before any HTTP call so it is never retried as transient.
    """
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        raise ValueError(f"limit must be a positive int, got {limit!r}")


def _validate_str_keys(d: dict, label: str) -> None:
    """Raise `_MalformedLogResponseError` if any key in `d` is not a `str`.

    Must run before `sorted(d.items())`: mixed/unorderable key types would
    otherwise make `sorted()` raise a raw `TypeError` instead of the
    diagnosable error every other validation failure here uses.
    """
    for key in d.keys():
        if not isinstance(key, str):
            raise _MalformedLogResponseError(
                f"unsupported {label} key {key!r}: {type(key).__name__}"
            )


def _validate_hashable_scalar_values(d: dict, label: str) -> None:
    """Raise `_MalformedLogResponseError` if any value in `d` is not a
    hashable scalar (`str`/`int`/`float`/`bool`/`None`).

    `LogEntry.stream_labels`/`metadata` must be hashable; an unhashable
    value would otherwise parse successfully here and only fail later, when
    the scheduler's flush-time dedup hashes the resulting `LogEntry`.
    """
    for key, value in d.items():
        if not isinstance(value, _HASHABLE_SCALAR_TYPES):
            raise _MalformedLogResponseError(
                f"unsupported {label} value for key {key!r}:"
                f" {type(value).__name__}: {value!r}"
            )


def _parse_log_entries(
    log_dict, limit: int, start: int, end: int
) -> Tuple[List[LogEntry], int]:
    """Convert a Loki `query_range`-shaped response into `LogEntry` records,
    retaining only the smallest-timestamp `limit` of them.

    Combines each `data.result[i].stream` label dict with that entry's
    `values` tuples (`[ts_ns, line]` or `[ts_ns, line, metadata_dict]`).
    Every examined record is validated strictly, regardless of whether it
    ends up retained: shape, `timestamp_ns` inside `[start, end)`, and
    hashable stream/metadata values. Any deviation raises
    `_MalformedLogResponseError` rather than silently defaulting or
    dropping the record, which would make a malformed response
    indistinguishable from a legitimately empty or partial one.

    Retention is bounded to O(`limit`) additional memory via an incremental
    max-heap (by timestamp) rather than materializing and sorting the full
    response. This bound is about entries retained by this parser only --
    `log_dict` has already been fully decoded into memory by the client
    layer before reaching this function.

    Returns `(retained, examined_count)`: `retained` holds at most `limit`
    entries, sorted ascending by timestamp -- the true smallest-`limit`
    records across the whole response. `examined_count` lets the caller
    detect an oversized response.
    """
    _validate_positive_int_limit(limit)

    if not isinstance(log_dict, dict):
        raise _MalformedLogResponseError(
            f"expected a dict response body, got {type(log_dict).__name__}"
        )
    data = log_dict.get("data")
    if not isinstance(data, dict):
        raise _MalformedLogResponseError("response missing/invalid 'data' key")
    result = data.get("result")
    if not isinstance(result, list):
        raise _MalformedLogResponseError("response missing/invalid 'data.result' key")

    # Bounded max-heap (by timestamp) of at most `limit` retained entries.
    # `heap[0]` is always the current largest-timestamp retained entry --
    # the eviction candidate -- since the key negates `timestamp_ns`.
    heap: List[Tuple[int, int, LogEntry]] = []
    insertion_index = 0
    examined = 0

    for item in result:
        if not isinstance(item, dict):
            raise _MalformedLogResponseError(
                f"expected a dict result entry, got {type(item).__name__}"
            )
        stream = item.get("stream")
        values = item.get("values")
        if not isinstance(stream, dict) or not isinstance(values, list):
            raise _MalformedLogResponseError(
                "result entry missing/invalid 'stream' or 'values' key"
            )
        # Validated once per stream, not per record: `stream` is unchanged
        # across this iteration's `values`.
        _validate_str_keys(stream, "stream")
        _validate_hashable_scalar_values(stream, "stream")
        stream_labels = tuple(sorted(stream.items()))
        for value in values:
            if not isinstance(value, (list, tuple)) or len(value) not in (2, 3):
                raise _MalformedLogResponseError(f"malformed values tuple: {value!r}")
            # bool is an int subclass and float silently truncates under
            # int() -- reject both explicitly rather than letting int()
            # below coerce them into a wrong-but-valid-looking timestamp.
            if isinstance(value[0], (bool, float)):
                raise _MalformedLogResponseError(
                    f"non-integer timestamp in values tuple: {value!r}"
                )
            try:
                timestamp_ns = int(value[0])
            except (TypeError, ValueError) as e:
                raise _MalformedLogResponseError(
                    f"non-integer timestamp in values tuple: {value!r}"
                ) from e
            if not (start <= timestamp_ns < end):
                raise _MalformedLogResponseError(
                    f"entry timestamp_ns={timestamp_ns} outside requested"
                    f" range=[{start}, {end})"
                )
            line = value[1]
            if not isinstance(line, str):
                raise _MalformedLogResponseError(
                    f"expected a str log line, got {type(line).__name__}: {line!r}"
                )
            metadata = ()
            if len(value) == 3 and value[2] is not None and value[2] != {}:
                # `None`/`{}` are the accepted "no metadata" forms; checked
                # by content, not truthiness, so a wrong-typed-but-falsy
                # value (`0`, `""`, `[]`) is still rejected below.
                if not isinstance(value[2], dict):
                    raise _MalformedLogResponseError(
                        "malformed metadata: expected a dict, got"
                        f" {type(value[2]).__name__}: {value[2]!r}"
                    )
                _validate_str_keys(value[2], "metadata")
                _validate_hashable_scalar_values(value[2], "metadata")
                metadata = tuple(sorted(value[2].items()))
            entry = LogEntry(stream_labels, timestamp_ns, line, metadata)
            examined += 1

            if len(heap) < limit:
                heapq.heappush(heap, (-timestamp_ns, insertion_index, entry))
                insertion_index += 1
            elif timestamp_ns < -heap[0][0]:
                heapq.heapreplace(heap, (-timestamp_ns, insertion_index, entry))
                insertion_index += 1

    retained = [entry for _, _, entry in heap]
    retained.sort(key=lambda e: e.timestamp_ns)
    return retained, examined


def _quiet_close(f) -> None:
    """Best-effort-close an open file handle, never raising or printing.

    Used by every early-exit-after-failure path in `run()` so content
    already streamed to disk is flushed before the process exits, without
    disturbing whatever primary failure message that path is about to
    report.
    """
    if f is None:
        return
    try:
        f.close()
    except OSError:
        pass


def _render_time_range_summary(
    first_utc_time: str, last_utc_time: str, total_lines: int, elapsed_sec: float
) -> str:
    """Render the `Time range: ... Total: ... Duration: ...` console block
    shared by both the `--path` and stdout completion branches of `run()`.
    """
    return (
        f"\n[bold]Time range[/]: [bold cyan]UTC|{first_utc_time}[/]"
        f" → [blue]UTC|{last_utc_time}[/]\n[bold]Total[/]:"
        f" [green]{total_lines}[/] lines \n[bold cyan]Duration[/]:"
        f" [magenta]{elapsed_sec:.2f}s[/]\n"
    )


def _render_file_footer_text(
    first_utc_time: str,
    last_utc_time: str,
    total_lines: int,
    failed_units: List[Tuple[int, int]],
) -> str:
    """Render the `--path` output file's footer: the neutral `Time range`
    line, plus a capped `PARTIAL RESULT` line naming failed ranges when
    `failed_units` is non-empty (the untruncated list still goes to the
    trace log).
    """
    text = (
        f"Time range: UTC|{first_utc_time} → "
        f"UTC|{last_utc_time} | total {total_lines} lines \n"
    )
    if failed_units:
        capped = failed_units[:_FAILED_RANGES_FILE_CAP]
        ranges_str = ", ".join(
            f"[{_epoch_to_time_str(s)}, {_epoch_to_time_str(e)})" for s, e in capped
        )
        remaining = len(failed_units) - len(capped)
        if remaining > 0:
            ranges_str += f" (+{remaining} more, see trace log for full list)"
            logger.trace(
                "adaptive fetch: full list of failed ranges:"
                f" {[(s, e) for s, e in failed_units]}"
            )
        text += (
            f"PARTIAL RESULT: {len(failed_units)} time"
            " range(s) could not be fetched and are missing from"
            f" this file: {ranges_str}\n"
        )
    return text


def _interruptible_sleep(delay: float, cancelled: Optional[threading.Event]) -> None:
    """Sleep `delay` seconds, waking early if `cancelled` is set.

    Uses `cancelled.wait(delay)` rather than `time.sleep(delay)` so a
    cancellation recorded mid-sleep -- including a `Retry-After`-bounded
    sleep up to 60s -- wakes the caller promptly instead of blocking for the
    remainder of the delay.
    """
    if cancelled is not None:
        cancelled.wait(delay)
    else:
        time.sleep(delay)


def _fixed_backoff_delay(attempt: int, base_delay: float) -> float:
    """Fixed exponential backoff delay for a non-429 retry attempt."""
    return base_delay * (2**attempt)


def _rate_limit_retry_delay(
    e: LogAPIError, attempt: int, base_delay: float, retry_after_cap: float
) -> float:
    """Delay before retrying a 429, honoring `Retry-After` when present
    (bounded to `retry_after_cap`), else jittered exponential backoff. This
    same value is also used as the shared rate-limit signal's cooldown.
    """
    if e.retry_after is not None:
        return min(e.retry_after, retry_after_cap)
    return min(retry_after_cap, base_delay * (2**attempt) * random.uniform(1.0, 1.5))


# Checks `cancelled` before the first attempt, before each retry sleep, and
# before a 429 sleep, so a cancellation is observed promptly rather than
# after a long sleep completes. Backoff/retry sleeps themselves are also
# interruptible mid-sleep via `_interruptible_sleep`.
def _fetch_log_unit(
    deployment,
    job,
    replica,
    job_history_name,
    query,
    start: int,
    end: int,
    limit: int = _ADAPTIVE_PAGE_LIMIT,
    cancelled: Optional[threading.Event] = None,
    rate_limit_signal: Optional[_RateLimitSignal] = None,
) -> FetchUnitResult:
    """Fetch exactly one page for `[start, end)`, forward-direction, with retry.

    Retried up to `_ADAPTIVE_RETRY_MAX_ATTEMPTS` times and returns a
    structured `FetchUnitResult` -- never loops or shrinks its own range;
    the scheduler owns splitting a saturated result into child `WorkUnit`s.
    A 429 honors `Retry-After` (bounded) or falls back to jittered
    exponential backoff and signals the shared `rate_limit_signal`; any
    other failure uses fixed exponential backoff. A running HTTP call
    cannot be forcibly aborted once started, so a unit already mid-request
    when cancellation is requested can still delay the caller by up to
    `_ADAPTIVE_FETCH_TIMEOUT_SEC`. `start`/`end` are validated by the CLI
    dispatch path before the scheduler's root work unit is ever
    constructed, so this loop's retries are only ever for a genuine
    backend/parse failure, never a precondition violation.
    """
    _validate_positive_int_limit(limit)

    client = APIClient()
    max_retries = _ADAPTIVE_RETRY_MAX_ATTEMPTS
    base_delay = _ADAPTIVE_RETRY_BASE_DELAY_SEC
    retry_after_cap = _ADAPTIVE_RETRY_AFTER_CAP_SEC

    for attempt in range(max_retries):
        if cancelled is not None and cancelled.is_set():
            return FetchUnitResult(
                entries=[], saturated=False, min_ts=None, max_ts=None, failed=True
            )
        try:
            logger.trace(
                f"fetching unit range=[{start}, {end})"
                f" attempt={attempt + 1}/{max_retries}"
            )
            log_dict = client.log.get_log(
                name_or_deployment=deployment,
                name_or_job=job,
                replica=replica,
                job_history_name=job_history_name,
                start=start,
                end=end,
                limit=limit,
                q=query,
                direction="forward",
                timeout=_ADAPTIVE_FETCH_TIMEOUT_SEC,
            )
            entries, examined_count = _parse_log_entries(log_dict, limit, start, end)

            if examined_count > limit:
                logger.trace(
                    f"unit range=[{start}, {end}) backend returned"
                    f" {examined_count} entries, exceeding limit={limit}; capped to"
                    f" {limit}"
                )

            min_ts = entries[0].timestamp_ns if entries else None
            max_ts = entries[-1].timestamp_ns if entries else None
            saturated = examined_count >= limit
            logger.trace(
                f"unit range=[{start}, {end}) fetched {len(entries)} entries"
                f" saturated={saturated}"
            )
            return FetchUnitResult(
                entries=entries,
                saturated=saturated,
                min_ts=min_ts,
                max_ts=max_ts,
                failed=False,
            )
        except Exception as e:
            # A single classified retry step for both `LogAPIError` (where
            # status-code/retry-after info is available) and any other
            # failure: only the delay selection differs -- 429s honor
            # `Retry-After` (capped) or fall back to jittered backoff and
            # signal the shared rate-limit signal; anything else uses fixed
            # exponential backoff. Cancellation-check-and-interruptible-sleep
            # is shared, run exactly once regardless of failure type.
            logger.trace(traceback.format_exc())
            logger.trace(e)
            if attempt >= max_retries - 1:
                break
            if cancelled is not None and cancelled.is_set():
                return FetchUnitResult(
                    entries=[], saturated=False, min_ts=None, max_ts=None, failed=True
                )
            if isinstance(e, LogAPIError) and e.status_code == 429:
                delay = _rate_limit_retry_delay(e, attempt, base_delay, retry_after_cap)
                if e.retry_after is not None:
                    logger.trace(
                        f"429 rate limit: unit=[{start},{end}) honoring"
                        f" Retry-After={e.retry_after}s (capped to {delay}s)"
                    )
                else:
                    logger.trace(
                        f"429 rate limit: unit=[{start},{end}) no Retry-After,"
                        f" jittered backoff={delay:.2f}s attempt={attempt + 1}"
                    )
                if rate_limit_signal is not None:
                    rate_limit_signal.signal(delay)
            else:
                delay = _fixed_backoff_delay(attempt, base_delay)
                logger.trace(
                    f"retrying unit range=[{start}, {end}) after {delay}s"
                    f" (attempt {attempt + 1}/{max_retries})"
                )
            _interruptible_sleep(delay, cancelled)

    logger.trace(f"unit range=[{start}, {end}) failed after {max_retries} retries")
    return FetchUnitResult(
        entries=[], saturated=False, min_ts=None, max_ts=None, failed=True
    )


class _EmitBookkeeping:
    """Running total_lines/first_utc_time/last_utc_time for the final summary.

    Updated by whichever sink (`_make_file_sink`/`_make_stdout_sink`) is
    active, in emitted (chronological) order.
    """

    def __init__(self):
        self.total_lines = 0
        self.first_utc_time: Optional[str] = None
        self.last_utc_time: Optional[str] = None

    def record(self, utc_time: str) -> None:
        if self.total_lines == 0:
            self.first_utc_time = utc_time
        self.last_utc_time = utc_time
        self.total_lines += 1


class _LazyFileSink:
    """The `--path` sink. Directory resolution and file opening are deferred
    to the first actual write need: until `ensure_open`/`emit` is first
    called, the filesystem is completely untouched -- no directory created,
    no file opened, no pre-existing file at `raw_path` truncated. `run()`
    triggers the deferred open from two call sites: the first emitted batch
    of entries (`emit`), or -- for a run that emits nothing but still has
    failure information worth recording -- explicitly via `ensure_open`
    right before the footer is written.
    """

    def __init__(
        self,
        raw_path: str,
        name_hint: str,
        without_timestamp: bool,
        bookkeeping: _EmitBookkeeping,
    ):
        self._raw_path = raw_path
        self._name_hint = name_hint
        self.without_timestamp = without_timestamp
        self.bookkeeping = bookkeeping
        # Set once `resolve_save_path` succeeds, independent of whether the
        # subsequent `open()` call itself then succeeds.
        self.path: Optional[str] = None
        self._f = None

    def ensure_open(self) -> None:
        """Resolve `raw_path` (creating its directory if needed) and open the
        file, if not already done. Idempotent: a no-op once the file is open.

        Raises `PathResolutionError` (directory creation failure) or
        `OSError` (file open failure) -- callers decide how to report and
        handle it, since the appropriate response differs depending on
        whether workers are still active.
        """
        if self._f is not None:
            return
        default_filename = (
            f"log-{self._name_hint}{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
        )
        self.path = resolve_save_path(self._raw_path, default_filename)
        self._f = open(self.path, "w", encoding="utf-8")

    def emit(self, entries: List[LogEntry]) -> None:
        self.ensure_open()
        for entry in entries:
            utc_time = _epoch_to_time_str(entry.timestamp_ns)
            cur_line = safe_load_json(entry.line)
            if self.without_timestamp:
                self._f.write(f"{cur_line}\n")
            else:
                self._f.write(f"{utc_time}｜{cur_line}\n")
            self.bookkeeping.record(utc_time)

    def write_footer(self, text: str) -> None:
        self._f.write(text)

    def close(self) -> None:
        self._f.close()

    def quiet_close(self) -> None:
        _quiet_close(self._f)


def _make_stdout_sink(without_timestamp: bool, bookkeeping: _EmitBookkeeping) -> EmitFn:
    """Build the no-`--path` sink: prints each entry via the shared `console`."""

    def emit(entries: List[LogEntry]) -> None:
        for entry in entries:
            utc_time = _epoch_to_time_str(entry.timestamp_ns)
            cur_line = safe_load_json(entry.line)
            if not without_timestamp:
                console.print(f"[green]{utc_time}|[/]", end="")
            console.print(json.dumps(cur_line, ensure_ascii=False), markup=False)
            bookkeeping.record(utc_time)

    return emit


class _AdaptiveLogScheduler:
    """Adaptive bisection scheduler for the no-`--limit` fetch path.

    Encapsulates the scheduler's mutable state (pending queue, active-future
    map, commit-watermark buffer, cancellation event, `seq_id` counter,
    progress bookkeeping, failed units, sink state) as instance attributes.
    All methods, including `run`, execute only on the single thread that owns
    the `ThreadPoolExecutor` context; worker threads only ever call the free
    function `_fetch_log_unit` and never touch scheduler state directly --
    they never enqueue work or allocate `seq_id`s themselves.
    """

    def __init__(
        self,
        deployment,
        job,
        replica,
        job_history_name,
        query,
        unix_start: int,
        unix_end: int,
        workers: Optional[int],
        without_timestamp: bool,
        path: Optional[str],
    ):
        """
        Args:
            path: the raw, unresolved `--path` value (may name a directory
                or a file, or be `None` for stdout) -- NOT yet resolved to a
                concrete file path. Resolution (which may create a
                directory) and opening the file are both deferred to the
                first actual write need, via `self.sink`; see
                `_LazyFileSink`.
        """
        self.deployment = deployment
        self.job = job
        self.replica = replica
        self.job_history_name = job_history_name
        self.query = query
        self.unix_start = unix_start
        self.unix_end = unix_end
        self.effective_workers = workers if workers is not None else 32
        self.without_timestamp = without_timestamp

        self.bookkeeping = _EmitBookkeeping()
        # Same default-filename precedence `fetch_log` used before path
        # resolution was made lazy: deployment/job/replica/job_history_name,
        # in that order, first truthy one wins.
        name_hint = job or deployment or replica or job_history_name or ""
        self.sink = (
            _LazyFileSink(path, name_hint, without_timestamp, self.bookkeeping)
            if path
            else None
        )

        self.cancelled = threading.Event()
        self.rate_limit_signal = _RateLimitSignal()
        self._seq_counter = itertools.count()

        # Min-heap keyed by WorkUnit's (start, seq_id) total order -- always
        # dispatches the smallest-`start` pending unit next, never FIFO.
        self.pending: List[WorkUnit] = []
        heapq.heappush(self.pending, WorkUnit(self._next_seq(), unix_start, unix_end))
        self.active = {}  # future -> WorkUnit

        self.buffer = (
            []
        )  # heap of (timestamp_ns, unit_seq_id, response_index, LogEntry)
        self.failed_units: List[Tuple[int, int]] = []

        # Admission-control cap for `_submit_ready`'s buffered-plus-reserved
        # accounting (see `cap_blocks` there): `effective_workers` in-flight
        # units can each contribute up to `_ADAPTIVE_PAGE_LIMIT` entries to
        # the buffer before the watermark advances past them, plus one unit
        # of slack. The frontier exemption (see `_submit_ready`) is the sole
        # source of a bounded one-page overshoot above this cap.
        self._max_buffered_entries = (self.effective_workers + 1) * _ADAPTIVE_PAGE_LIMIT

        self.last_watermark = unix_start
        self.progress_total = 1

    def _next_seq(self) -> int:
        """Allocate the next `WorkUnit.seq_id` from the counter.

        Only ever called from the scheduler's owning thread (the
        constructor, called once, and `_handle_result`, called only from
        `run()`'s main loop) -- worker threads never enqueue work or
        allocate sequence IDs themselves, only ever call the free function
        `_fetch_log_unit` and return `FetchUnitResult` values.
        """
        return next(self._seq_counter)

    def _admission_blocked(self) -> bool:
        """Whether admission control currently blocks submitting another unit.

        Bounds the resident-entry count (buffered + reserved-for-active,
        accounting for the unit about to be admitted) to
        self._max_buffered_entries. `len(active) >= 1` is mandatory, not an
        optimization: it exempts the frontier (smallest-start) pending unit
        from ever being blocked when nothing is in flight, which is what
        guarantees the scheduler always has a path to advance the watermark
        and can never deadlock with pending work and nothing submitted --
        the sole source of a bounded one-page overshoot above the cap.
        """
        return (
            len(self.active) >= 1
            and (len(self.buffer) + (len(self.active) + 1) * _ADAPTIVE_PAGE_LIMIT)
            > self._max_buffered_entries
        )

    def _submit_ready(self, executor: ThreadPoolExecutor) -> None:
        """Fill the active-future map up to `effective_workers` from the pending queue.

        Never more than `effective_workers` `_fetch_log_unit` calls in flight
        at once, no new submissions once `cancelled` is set, and always
        dispatches the smallest-`(start, seq_id)` pending unit, never FIFO.
        While the shared rate-limit signal is active, zero new submissions
        are made this pass; already-active units continue uninterrupted.
        Also gated by `_admission_blocked` below -- except the frontier
        (smallest-`start`) unit is never blocked by it when nothing is
        active.
        """
        while (
            self.pending
            and len(self.active) < self.effective_workers
            and not (self.cancelled.is_set() or self.rate_limit_signal.active())
        ):
            if self._admission_blocked():
                break

            unit = heapq.heappop(self.pending)
            future = executor.submit(
                _fetch_log_unit,
                self.deployment,
                self.job,
                self.replica,
                self.job_history_name,
                self.query,
                unit.start,
                unit.end,
                _ADAPTIVE_PAGE_LIMIT,
                self.cancelled,
                self.rate_limit_signal,
            )
            self.active[future] = unit
            logger.trace(
                f"submitted unit seq={unit.seq_id} range=[{unit.start}, {unit.end})"
            )

    def _handle_result(self, unit: WorkUnit, result: FetchUnitResult) -> bool:
        """Process one completed unit's `FetchUnitResult`: buffer entries and,
        on saturation, enqueue bisected children of the unscanned remainder.

        The same-timestamp saturation check (Case A/B below) always takes
        priority over the general single-vs-two-child bisection heuristic --
        it must be evaluated first to keep sibling-split coverage gap-free
        and duplicate-free outside the one accepted same-timestamp
        exception. Returns whether progress should advance by one unit
        (False when the unit was split, since children were added to the
        total instead).
        """
        progress_advance = True

        if result.failed:
            self.failed_units.append((unit.start, unit.end))
            logger.trace(
                f"unit seq={unit.seq_id} range=[{unit.start}, {unit.end}) failed"
                " after retries"
            )
            return progress_advance

        if not result.entries:
            logger.trace(
                f"unit seq={unit.seq_id} range=[{unit.start}, {unit.end}) empty"
            )
            return progress_advance

        for idx, entry in enumerate(result.entries):
            heapq.heappush(self.buffer, (entry.timestamp_ns, unit.seq_id, idx, entry))

        if not result.saturated:
            return progress_advance

        split_point = result.max_ts

        # Case A -- width-<=1ns remainder (terminal): [T, unit.end) cannot
        # contain more than one distinct ns value going forward. No valid
        # mid exists to bisect around, so the unit resolves with zero
        # children.
        if split_point >= unit.end - 1:
            logger.trace(
                "same-timestamp saturation safeguard: unit="
                f"{unit.seq_id} range=[{unit.start},{unit.end}) ts={split_point}"
                f" limit={_ADAPTIVE_PAGE_LIMIT} — output for this timestamp may"
                " be incomplete"
            )
            return progress_advance

        # Case B -- saturated single-timestamp page (continues past T): the
        # whole page shares timestamp_ns == T, so the page could not see
        # past T -- this does not mean (T, unit.end) is empty. The T group
        # is resolved via the existing flush-time dedup/cap safeguard
        # (accepted tradeoff), but scanning continues by enqueuing a single
        # child at [T + 1, unit.end). T + 1 is safe only in this branch --
        # never in the general saturated-boundary handling below.
        if result.min_ts == split_point:
            child = WorkUnit(self._next_seq(), split_point + 1, unit.end)
            heapq.heappush(self.pending, child)
            progress_advance = False
            logger.trace(
                "same-timestamp saturation safeguard: unit="
                f"{unit.seq_id} range=[{unit.start},{unit.end}) ts={split_point}"
                f" limit={_ADAPTIVE_PAGE_LIMIT} — T group capped/deduplicated,"
                " continuing scan at T+1"
            )
            return progress_advance

        # Whether to bisect the unscanned remainder [T, unit.end) or hand it
        # off whole depends on WHERE in the originally-fetched interval
        # saturation occurred (not on the remainder itself): late saturation
        # suggests a small remainder (single unsplit child; it can still
        # split further next time it saturates), early saturation suggests
        # a dense remainder (split immediately).
        #
        # branch_mid MUST use true (float) division, never integer floor
        # division: at an odd-sum interval, floor division rounds the
        # midpoint down by half a nanosecond and can silently flip the
        # branch decision.
        branch_mid = (unit.start + unit.end) / 2
        if split_point >= branch_mid:
            child = WorkUnit(self._next_seq(), split_point, unit.end)
            assert child.start == split_point and child.end == unit.end
            heapq.heappush(self.pending, child)
            progress_advance = False
            logger.trace(
                "split unit (single child, saturation at/past fetched midpoint)"
                f" seq={unit.seq_id} range=[{unit.start}, {unit.end}) at"
                f" T={split_point} branch_mid={branch_mid} into"
                f" child=[{child.start}, {child.end})"
            )
        else:
            mid = split_point + (unit.end - split_point) // 2
            left = WorkUnit(self._next_seq(), split_point, mid)
            right = WorkUnit(self._next_seq(), mid, unit.end)
            assert (
                left.end == right.start
                and left.start == split_point
                and right.end == unit.end
            )
            heapq.heappush(self.pending, left)
            heapq.heappush(self.pending, right)
            self.progress_total += 1
            progress_advance = False
            logger.trace(
                "split unit (two children, saturation before fetched midpoint)"
                f" seq={unit.seq_id} range=[{unit.start}, {unit.end}) at"
                f" T={split_point} branch_mid={branch_mid} into"
                f" left=[{left.start}, {left.end}) right=[{right.start}, {right.end})"
            )

        return progress_advance

    def _compute_watermark(self) -> int:
        """Recompute the commit watermark: the minimum `start` across all
        pending-or-active units, or `unix_end` once none remain.

        The watermark never regresses -- `run` raises
        `_WatermarkRegressionError`, a handled failure, if it ever does.
        """
        starts = [u.start for u in self.pending]
        starts.extend(u.start for u in self.active.values())
        return min(starts) if starts else self.unix_end

    def _drain_and_emit(self, watermark: int, emit_fn: EmitFn) -> None:
        """Pop and emit all buffered entries strictly below `watermark`,
        de-duplicating exact `LogEntry` repeats at flush time.
        """
        to_emit: List[LogEntry] = []
        seen = set()
        while self.buffer and self.buffer[0][0] < watermark:
            _, _, _, entry = heapq.heappop(self.buffer)
            if entry in seen:
                continue
            seen.add(entry)
            to_emit.append(entry)
        if to_emit:
            emit_fn(to_emit)

    def run(self) -> NoReturn:
        """Run the scheduler loop to completion and terminate the process.

        Drives the fill/wait/handle-result loop over a `ThreadPoolExecutor`
        bounded by `effective_workers`, then prints the final summary and
        exits: 0 on success, 1 on sink failure, 2 on partial fetch failure.
        On sink failure, `cancelled` is set and no further units are
        submitted; a unit already inside a blocking HTTP call still delays
        shutdown up to `_ADAPTIVE_FETCH_TIMEOUT_SEC`, since `future.cancel()`
        cannot abort a call already in flight. This is the only method that
        calls `sys.exit`, and the only one that triggers `self.sink`'s lazy
        open (via `emit_fn` or, at finalization, a direct `ensure_open`
        call) -- see `_LazyFileSink`.
        """
        start_perf = time.perf_counter()

        emit_fn = (
            self.sink.emit
            if self.sink
            else _make_stdout_sink(self.without_timestamp, self.bookkeeping)
        )

        progress_cm = Progress() if self.sink else contextlib.nullcontext()
        sink_exc = None
        watermark_exc: Optional[_WatermarkRegressionError] = None

        # `self.sink`, once open, stays open (no `finally: close()`) so the
        # footer can be written through the same handle later. Each error
        # exit path below (including BrokenPipeError) does a silent
        # best-effort close right before exiting, to flush already-streamed
        # content without disturbing that path's own primary error message.
        with progress_cm as progress:
            task = (
                progress.add_task("Fetching logs...", total=self.progress_total)
                if self.sink
                else None
            )

            with ThreadPoolExecutor(max_workers=self.effective_workers) as executor:
                while (
                    (self.pending or self.active)
                    and sink_exc is None
                    and watermark_exc is None
                ):
                    self._submit_ready(executor)

                    if not self.active:
                        if self.cancelled.is_set() or not self.pending:
                            break
                        # Nothing in flight, likely because the rate-limit
                        # signal is blocking new submissions. Wait briefly
                        # rather than exiting with pending work undone.
                        time.sleep(0.05)
                        continue

                    done, _ = wait(
                        list(self.active.keys()), return_when=FIRST_COMPLETED
                    )
                    for future in done:
                        unit = self.active.pop(future)
                        if self.cancelled.is_set():
                            continue

                        result = future.result()
                        progress_advance = self._handle_result(unit, result)

                        if self.sink:
                            if progress_advance:
                                progress.update(task, advance=1)
                            else:
                                progress.update(task, total=self.progress_total)

                        # Handled control-flow branch, not a bare `assert`
                        # (which raises uncaught and is compiled out under
                        # -O).
                        try:
                            watermark = self._compute_watermark()
                            if watermark < self.last_watermark:
                                raise _WatermarkRegressionError(
                                    "watermark regressed from"
                                    f" {self.last_watermark} to {watermark}"
                                )
                            self.last_watermark = watermark
                            logger.trace(f"watermark advanced to {watermark}")

                            self._drain_and_emit(watermark, emit_fn)
                        except _WatermarkRegressionError as e:
                            self.cancelled.set()
                            watermark_exc = e
                            break
                        except BrokenPipeError:
                            self.cancelled.set()
                            if self.sink is not None:
                                self.sink.quiet_close()
                            raise
                        except Exception as e:
                            self.cancelled.set()
                            sink_exc = e
                            break

                # Fail-fast shutdown: cancel not-yet-started futures and join the rest.
                for future in list(self.active.keys()):
                    future.cancel()

        if watermark_exc is not None:
            if self.sink is not None:
                self.sink.quiet_close()
            console.print(f"[red]Internal scheduling error[/]: {watermark_exc}")
            sys.exit(1)

        if sink_exc is not None:
            if self.sink is not None:
                self.sink.quiet_close()
            console.print(f"[red]Failed to write logs[/]: {sink_exc}")
            sys.exit(1)

        elapsed_sec = time.perf_counter() - start_perf
        first_utc_time = self.bookkeeping.first_utc_time or _epoch_to_time_str(
            self.unix_start
        )
        last_utc_time = self.bookkeeping.last_utc_time or _epoch_to_time_str(
            self.unix_end
        )
        total_lines = self.bookkeeping.total_lines

        # Every unit genuinely succeeded and found nothing (as opposed to
        # some units failing, where we don't actually know). `self.sink` is
        # guaranteed to still be unopened here (nothing was ever emitted,
        # and this branch is reached before the failed-units footer-write
        # path below could have opened it), so for `--path` the filesystem
        # is completely untouched: no directory created, no file opened.
        if total_lines == 0 and not self.failed_units:
            console.print("[yellow]No logs found in the specified time range.[/]")
            sys.exit(0)

        if self.failed_units:
            ranges_str = ", ".join(
                f"[{_epoch_to_time_str(s)}, {_epoch_to_time_str(e)})"
                for s, e in self.failed_units
            )
            console.print(
                f"[yellow]Warning[/]: {len(self.failed_units)} time range(s) could"
                " not be fetched after 5 retries and are missing from the output:"
                f" {ranges_str}"
            )

        logger.trace(
            f"adaptive fetch complete: total_lines={total_lines}"
            f" failed_units={len(self.failed_units)}"
        )

        if self.sink is not None:
            # Reaching here with `self.sink` still unopened means nothing
            # was ever emitted but `self.failed_units` is non-empty (a
            # partial run must still produce its output file, with the
            # failure-summary footer, even at total_lines == 0) -- open it
            # now, lazily, right before the footer is written.
            try:
                self.sink.ensure_open()
            except (PathResolutionError, OSError) as e:
                console.print(f"[red]Failed to write logs[/]: {e}")
                sys.exit(1)

            # Footer written through the same still-open handle used for
            # streaming entries -- no second `open(path, "a")` call.
            try:
                self.sink.write_footer(
                    _render_file_footer_text(
                        first_utc_time, last_utc_time, total_lines, self.failed_units
                    )
                )
            except OSError as e:
                # Footer write failed: silent best-effort close so entries
                # already streamed are flushed, even though the footer
                # itself is absent/incomplete. Never raises/prints its own
                # message -- only the footer-write failure below is
                # reported, and the write is not retried after closing.
                self.sink.quiet_close()
                console.print(f"[red]Failed to write log file footer[/]: {e}")
                sys.exit(1)

            try:
                self.sink.close()
            except OSError as e:
                # Close failure after a successful footer write still exits
                # 1 without printing success/partial text, even though the
                # footer content was already flushed.
                console.print(f"[red]Failed to close output file[/]: {e}")
                sys.exit(1)

            console.print(
                _render_time_range_summary(
                    first_utc_time, last_utc_time, total_lines, elapsed_sec
                )
            )
            if self.failed_units:
                console.print(
                    "\n[bold yellow]Partial result[/bold yellow]: saved"
                    f" incomplete log to: {self.sink.path}\n"
                )
            else:
                console.print(
                    "\n[bold green]Successfully saved the log"
                    f" to:[/bold green] {self.sink.path}\n"
                )
        else:
            console.print(
                f"\n👆Time range: [blue]UTC|{first_utc_time}[/] →"
                f" [blue]UTC|{last_utc_time}[/] total"
                f" [green]{total_lines}[/] lines \n"
            )
            if self.failed_units:
                console.print(
                    "\n[bold yellow]Partial result[/bold yellow]: log output"
                    " is incomplete\n"
                )

        sys.exit(2 if self.failed_units else 0)


def fetch_logs_adaptive_parallel(
    deployment,
    job,
    replica,
    job_history_name,
    query,
    unix_start: int,
    unix_end: int,
    workers: Optional[int],
    without_timestamp: bool,
    path: Optional[str],
) -> NoReturn:
    """Construct and run an `_AdaptiveLogScheduler` for one fetch.

    `path` is the raw, unresolved `--path` value (a directory, a file path,
    or `None` for stdout) -- resolution and file creation are deferred by
    the scheduler itself until actually needed; see `_LazyFileSink`.
    Terminal: always calls `sys.exit(...)` and never returns (see
    `_AdaptiveLogScheduler.run`).
    """
    _AdaptiveLogScheduler(
        deployment,
        job,
        replica,
        job_history_name,
        query,
        unix_start,
        unix_end,
        workers,
        without_timestamp,
        path,
    ).run()


@click_group()
def log():
    """
    Manage and retrieve the logs history of specific jobs, deployments and replicas.\n
    IMPORTANT: \n
    - 'lep log get' and 'lep log get --path' are intended for quick, time-scoped viewing.\n
    - They are NOT recommended for downloading logs \n
    - Prefer using Workspace Dashboard -> Settings -> Logs Export for downloading
      large-volume logs (jobs/endpoints long-running or with many replicas). \n
    - When --limit is NOT used, retrieval adapts to the requested range: workers
      fetch it in parallel and only split further when a fetch saturates the
      per-request page limit, so the number of requests made depends on how
      dense the logs are, not on a fixed number of windows. \n
    - Concurrency (workers) is applied only when --limit is NOT used. \n
    - --limit is deprecated and not recommended. When set, logs will be fetched
      sequentially without parallelism. It will be removed in a future release. \n
    - Interactive mode (next/last/time+/time-) is deprecated and not recommended.
      It will be removed in a future release. \n

    JOB DEFAULT TIME RANGE: \n
    - For jobs, --start/--end can be omitted. If omitted, the job's creation_time
      and completion_time (when available) will be used automatically; if the job
      has not completed, end defaults to 'now'.
    """
    pass


@log.command(
    name="get", help="Retrieve and display logs from endpoints, jobs, or replicas"
)
@click.option(
    "--endpoint",
    "-e",
    "deployment",  # internal parameter name
    type=str,
    default=None,
    help="The name of the endpoint.",
)
@click.option(
    "--job",
    "-j",
    type=str,
    default=None,
    help=(
        "Specifies the job ID. To find the job ID, use 'lep job list'. "
        "When using --job, you may omit --start/--end: we'll use the job's "
        "creation_time and completion_time when available; if the job "
        "hasn't completed, end defaults to 'now'."
    ),
)
@click.option(
    "--job-name",
    "-jn",
    type=str,
    default=None,
    help=(
        "Specifies the job name. If multiple jobs share this name, the newest job "
        "is used by default. When using --job-name, you may omit --start/--end: "
        "we'll use the job's creation_time and completion_time when available; "
        "if the job hasn't completed, end defaults to 'now'."
    ),
)
@click.option(
    "--replica",
    type=str,
    default=None,
    help="The name of the replica or a Replica object.",
)
@click.option(
    "--job-history-name",
    type=str,
    default=None,
    help="The name of the job history.",
    hidden=True,
)
@click.option(
    "--start",
    type=str,
    default=None,
    help="The start time in ISO format. " + _supported_formats_log,
)
@click.option(
    "--end",
    type=str,
    default=None,
    help="The end time in ISO format. " + _supported_formats_log,
)
@click.option(
    "--limit",
    type=click.IntRange(min=1),
    default=None,
    help="[Deprecated] This option is deprecated and not recommended.",
    hidden=True,
)
@click.option(
    "--path",
    type=click.Path(
        exists=False,
        file_okay=True,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
    default=None,
    show_default=True,
    help="Local directory path to save the log TXT files.",
)
@click.option(
    "--query",
    type=str,
    default="",
    help="Specify the query string",
)
@click.option(
    "--without-timestamp",
    is_flag=True,
    default=False,
    help="Without timestamp",
)
@click.option(
    "--workers",
    "-w",
    type=click.IntRange(1, 128),
    default=None,
    show_default=False,
    help=(
        "Set the number of concurrent worker threads for fetching logs. "
        "Effective only when --limit is not used. Defaults to 32 when unspecified. "
        "Note: --limit is deprecated and not recommended."
    ),
)
def log_command(
    deployment,
    job,
    job_name,
    replica,
    job_history_name,
    start,
    end,
    limit,
    path,
    query,
    without_timestamp,
    workers,
):
    """
    Retrieve and display logs from deployments, jobs, or replicas.

    IMPORTANT:
    - 'lep log get' and 'lep log get --path' are intended is for quick, time-scoped viewing.
    - They are NOT recommended for downloading logs.
    - Prefer using Workspace Dashboard -> Settings -> Logs Export for downloading
      large-volume logs (jobs/endpoints long-running or with many replicas).
    - When --limit is NOT used, retrieval adapts to the requested range: workers
      fetch it in parallel and only split further when a fetch saturates the
      per-request page limit, so the number of requests made depends on how
      dense the logs are, not on a fixed number of windows.
    - Concurrency (workers) is applied only when --limit is NOT used.
    - --limit is deprecated and not recommended. When set, logs will be fetched
      sequentially without parallelism. It will be removed in a future release.
    - Interactive mode (next/last/time+/time-) is deprecated and not recommended.
      It will be removed in a future release.

    JOB DEFAULT TIME RANGE:
    - For jobs, --start/--end can be omitted. If omitted, the job's creation_time
      and completion_time (when available) will be used automatically.

    EXAMPLE:
    # Get logs from a job by ID using default job time range
    lep log get -j job-abc123
    lep log get -j job-abc123 --path ./logs/

    TIME FORMATS:
    All times must be in UTC. Supported formats include:
    - 'now' - Current UTC time
    - 'today' or 'td' - Today at midnight UTC (can add time: 'today 14:30')
    - 'yesterday' or 'yd' - Yesterday at midnight UTC (can add time: 'yesterday 09:15')
    - Full datetime: '2024-12-25 13:10:01.123456' or '2024/12/25 13:10:01.123456'

    EXAMPLES:
    # Get logs from a deployment for the last hour
    lep log get -d my-deployment --start "today 13:00" --end "today 14:00"

    # Get logs from a job by name for today
    lep log get -jn my-job-name --start today --end now

    # Get logs from a specific job ID with query filter
    lep log get -j job-abc123 --start yesterday --end today --query "error"

    # Save logs to file
    lep log get -d my-deployment --start "today 09:00" --end now --path ./logs/
    """

    if (
        not deployment
        and not job
        and not job_name
        and not replica
        and not job_history_name
    ):
        console.print(
            "[red]No deployment name, job id, job name or replica id provided.[/red]"
        )
        sys.exit(1)

    if sum(bool(var) for var in [deployment, job, job_name, job_history_name]) > 1:
        raise ValueError(
            "Only one of 'deployment', 'job', or 'job_history_name' can be specified."
        )

    client = APIClient()

    if job_name is not None:
        job = _get_newest_job_by_name(job_name)
        if job is None:
            console.print(
                f"[bold red]Warning:[/bold red] No job named '{job_name}' found."
            )
            sys.exit(1)
        job = job.metadata.id_

    if deployment:
        client.deployment.get(deployment)
    if job and not job_name:
        client.job.get(job)

    if (job or deployment) and replica:
        replicas = (
            client.job.get_replicas(job)
            if job
            else client.deployment.get_replicas(deployment)
        )
        if replica not in [replica.metadata.id_ for replica in replicas]:
            console.print(
                f"[bold red]Warning:[/bold red] No replica named '{replica}' found for"
                f" {job if job else deployment}."
            )
            sys.exit(1)

    if (not start or not end) and job:
        job_obj = client.job.get(job)
        logger.trace(json.dumps(job_obj.model_dump(), indent=4))
        if job_obj.status is not None:
            start = start or job_obj.status.creation_time
            end = end or job_obj.status.completion_time

    if not end:
        console.print("[red]Warning[/red] No end time provided. will be set to Now")
        end = "now"
    if not start:
        console.print(
            "[red]Warning[/red] No start time provided. will be set to today (today"
            " 00:00:00)"
        )
        start = "today"

    def fetch_log(start, end, limit, path=None):
        unix_start = _preprocess_time(start, epoch=True)
        unix_end = _preprocess_time(end, epoch=True)
        if unix_end <= unix_start:
            console.print(
                "[red]Warning[/red] End time must be greater than start time."
            )
            sys.exit(1)

        if limit is None:
            # Reject a non-positive start/end at the CLI boundary, before
            # any request is dispatched: mirrors LogAPI.get_log's own
            # _is_epoch_zero/negative rejection semantics, but enforced here
            # so an invalid range fails immediately (no worker dispatched,
            # no retry loop) instead of being discovered the slow way by
            # `_fetch_log_unit`'s retry machinery on the root work unit.
            if unix_start <= 0 or unix_end <= 0:
                console.print(
                    "[red]Warning[/red] start/end must be a positive"
                    " (non-zero) epoch timestamp for adaptive log"
                    " retrieval; 0 cannot be distinguished from an omitted"
                    " value, and negative timestamps are not valid."
                )
                sys.exit(1)

            # Path resolution (including any directory creation) is
            # deferred to the scheduler itself -- see
            # `_AdaptiveLogScheduler`/`_LazyFileSink` -- so a genuinely
            # empty adaptive result never creates a directory or file.
            #
            # Terminal: fetch_logs_adaptive_parallel always sys.exit()s and
            # never returns to this caller.
            fetch_logs_adaptive_parallel(
                deployment,
                job,
                replica,
                job_history_name,
                query,
                unix_start,
                unix_end,
                workers,
                without_timestamp,
                path,
            )

        # ======================================================================
        # LEGACY MODE
        # The following code is legacy and will be removed in the future.
        # Everything below handles the "limit" workflow for log processing and
        # output. Keep in mind this entire section is considered legacy.
        # ======================================================================
        log_list = []
        cur_unix_end = unix_end
        cur_limit = limit
        time_total_ns = max(1, unix_end - unix_start)
        with Progress() as progress:
            task = progress.add_task("Fetching logs...", total=time_total_ns)
            while cur_limit > 0:
                log_dict = client.log.get_log(
                    name_or_deployment=deployment,
                    name_or_job=job,
                    replica=replica,
                    job_history_name=job_history_name,
                    start=unix_start,
                    end=cur_unix_end,
                    limit=cur_limit if cur_limit < 10000 else 10000,
                    q=query,
                )
                lines = log_dict["data"]["result"]

                cur_log_list = []
                for line in lines:
                    values = line["values"]
                    for value in values:
                        cur_log_list.append((int(value[0]), value[1]))

                if len(cur_log_list) == 0:
                    progress.update(task, completed=True)
                    break
                # By setting reverse=True, the resulting list will be ordered from newest to oldest.
                # The subsequent while loop also produces a list from newest to oldest, allowing us
                # to easily extend them and, if desired, reverse the final combined list just once.
                cur_log_list.sort(key=lambda x: x[0], reverse=True)

                cur_limit -= len(cur_log_list)
                prev_unix_end = cur_unix_end
                cur_unix_end = cur_log_list[-1][0]
                progress.update(task, advance=prev_unix_end - cur_unix_end)

                log_list.extend(cur_log_list)

        return log_list

    def fetch_and_print_logs(start, end, limit, path=None):
        if path and limit is not None:
            default_filename = (
                f"log-{job or deployment or replica or job_history_name or ''}{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
            )
            try:
                path = resolve_save_path(path, default_filename)
            except PathResolutionError as e:
                console.print(
                    "[red][ERROR]failed to create directory:[/]"
                    f" {e.directory} ({e.cause})"
                )
                sys.exit(1)

        log_list = fetch_log(start, end, limit, path)

        # ======================================================================
        # LEGACY MODE
        # The following code is legacy and will be removed in the future.
        # Everything below handles the "limit" workflow for log processing and
        # output. Keep in mind this entire section is considered legacy.
        # ======================================================================
        first_utc_time = (
            _epoch_to_time_str(log_list[-1][0]) if len(log_list) > 0 else start
        )
        last_utc_time = _epoch_to_time_str(log_list[0][0]) if len(log_list) > 0 else end
        if path and limit is not None:
            with open(path, "w", encoding="utf-8") as f:
                f.write(
                    f"Time range: UTC|{first_utc_time} → "
                    f"UTC|{last_utc_time} | total {len(log_list)} lines \n"
                )
                for log in reversed(log_list):
                    utc_time = _epoch_to_time_str(log[0])
                    cur_line = safe_load_json(log[1])
                    if without_timestamp:
                        f.write(f"{cur_line}\n")
                    else:
                        f.write(f"{utc_time}｜{cur_line}\n")
            console.print(
                f"Time range: UTC|{first_utc_time} → "
                f"UTC|{last_utc_time} | total {len(log_list)} lines \n"
            )
            console.print(
                f"\n[bold green]Successfully saved the log to:[/bold green] {path}\n"
            )
            sys.exit(0)
        else:
            for log in reversed(log_list):
                utc_time = _epoch_to_time_str(log[0])
                cur_line = safe_load_json(log[1])
                if not without_timestamp:
                    console.print(f"[green]{utc_time}|[/]", end="")
                console.print(json.dumps(cur_line, ensure_ascii=False), markup=False)

            console.print(
                f"\n👆Time range: [blue]UTC|{first_utc_time}[/] →"
                f" [blue]UTC|{last_utc_time}[/] total"
                f" [green]{len(log_list)}[/] lines \n"
            )
        return first_utc_time, last_utc_time

    if not limit:
        # Adaptive (no-`--limit`) path: dispatch straight into the adaptive
        # scheduler. Its own root work unit fetches this exact
        # `[start, end)` interval immediately, so a separate one-record
        # probe request first would be redundant.
        fetch_and_print_logs(start, end, limit, path)
    else:
        # LEGACY MODE (deprecated `--limit` path): probe first for a quick
        # empty-range check before fetching sequentially.
        try:
            unix_start_probe = _preprocess_time(start, epoch=True)
            unix_end_probe = _preprocess_time(end, epoch=True)
            probe = client.log.get_log(
                name_or_deployment=deployment,
                name_or_job=job,
                replica=replica,
                job_history_name=job_history_name,
                start=unix_start_probe,
                end=unix_end_probe,
                limit=1,
                q=query,
            )
            if not probe or not probe.get("data", {}).get("result"):
                console.print("[yellow]No logs found in the specified time range.[/]")
                sys.exit(0)
        except Exception as e:
            console.print(f"[red]Failed to query logs[/]: {e}")
            sys.exit(1)

        first_utc_time, last_utc_time = fetch_and_print_logs(start, end, limit, path)
        while True and sys.stdin.isatty():
            console.print(
                "Enter a command [yellow](e.g., `next 10`, `last 20`, `time+ 30.5s`,"
                " `time- 2.1s`, `quit`)[/]:"
            )
            user_input = input().strip()
            if user_input.lower() in ["q", "quit", "exit"]:
                console.print("[lightblue]Exiting log viewer.[/]")
                break

            cmd_parts = user_input.split()
            if (
                cmd_parts is None
                or len(cmd_parts) != 2
                or cmd_parts[0] not in ["next", "last", "time+", "time-"]
            ):
                console.print(
                    "[red]Invalid command[/] we only accept next, last, time+ and time-"
                )
                continue
            cmd, param = cmd_parts

            if cmd == "next":
                try:
                    line_count = int(param)
                except (IndexError, ValueError):
                    console.print("[red]Please specify a valid number of lines.[/red]")
                    continue
                first_utc_time, last_utc_time = fetch_and_print_logs(
                    last_utc_time, "now", line_count
                )

            elif cmd == "last":
                try:
                    line_count = int(param)
                except (IndexError, ValueError):
                    console.print("[red]Please specify a valid number of lines.[/red]")
                    continue
                first_utc_time, last_utc_time = fetch_and_print_logs(
                    "search_before," + first_utc_time, first_utc_time, line_count
                )
            elif cmd == "time+" or cmd == "time-":
                pattern = r"^\d+(\.\d+)?s$"
                if not re.match(pattern, param):
                    console.print(
                        "[red]Invalid offset format. Expected something like"
                        " '2.567s'.[/]"
                    )
                    continue

                seconds_str = param[:-1]
                try:
                    float_seconds = float(seconds_str)
                except ValueError:
                    console.print(
                        f"[red]Failed to parse the numeric value {seconds_str} in the"
                        " offset.[/red]"
                    )
                    continue

                int_seconds = int(float_seconds)
                microseconds = int((float_seconds - int_seconds) * 1_000_000)

                if cmd == "time+":
                    last_utc_time_obj = _preprocess_time(last_utc_time)
                    adjusted_last_utc_time = last_utc_time_obj + timedelta(
                        seconds=int_seconds, microseconds=microseconds
                    )
                    adjusted_last_utc_time = adjusted_last_utc_time.strftime(
                        str_time_format
                    )
                    first_utc_time, last_utc_time = fetch_and_print_logs(
                        last_utc_time, adjusted_last_utc_time, 5000
                    )

                if cmd == "time-":
                    first_utc_time_obj = _preprocess_time(first_utc_time)
                    adjusted_first_utc_time = first_utc_time_obj - timedelta(
                        seconds=int_seconds, microseconds=microseconds
                    )
                    adjusted_first_utc_time = adjusted_first_utc_time.strftime(
                        str_time_format
                    )
                    first_utc_time, last_utc_time = fetch_and_print_logs(
                        adjusted_first_utc_time, first_utc_time, 5000
                    )


def add_command(cli_group):
    cli_group.add_command(log)
