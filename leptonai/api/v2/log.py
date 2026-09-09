from typing import Any, Dict, Optional, Union

from leptonai.api.v2.api_resource import APIResourse
from leptonai.api.v2.types.deployment import LeptonDeployment
from leptonai.api.v2.types.job import LeptonJob
from leptonai.api.v2.types.replica import Replica
from leptonai.api.v2.types.job import LeptonJobQueryMode


class LogAPIError(RuntimeError):
    """Structured error raised by `LogAPI.get_log` on any non-2xx `/logs` response.

    A `RuntimeError` subclass so `str(e)` and exception-handling behavior for
    every existing non-429 caller (the probe, the LEGACY path,
    `_fetch_log_unit`'s generic `except Exception` branch) is unchanged from
    today's bare `RuntimeError`. `status_code`/`retry_after` are new,
    additive attributes callers may optionally inspect.
    """

    def __init__(
        self, message: str, status_code: int, retry_after: Optional[float] = None
    ):
        super().__init__(message)
        self.status_code = status_code
        # Seconds, parsed from the response's `Retry-After` header when present
        # and in delay-in-seconds form; `None` otherwise.
        self.retry_after = retry_after


def _is_epoch_zero(value) -> bool:
    """Whether `value` represents an epoch timestamp of zero.

    Matches the Python `int` `0`, or a `str` that parses via `int(...)`
    (after stripping whitespace) to `0` -- e.g. `"0"`, `"00"`, `" 0 "`.
    Deliberately uses `int(...)` rather than `float(...)`, so a value like
    `"0.0"` is not treated as zero, and a non-numeric string is not either
    (a `ValueError` from `int(...)` means "not zero", it is not caught and
    reinterpreted). Any other type is never treated as zero.
    """
    if isinstance(value, int):
        return value == 0
    if isinstance(value, str):
        try:
            return int(value.strip()) == 0
        except ValueError:
            return False
    return False


def _to_epoch_int(value) -> Optional[int]:
    """Best-effort coercion of a start/end value to int for comparison.

    Mirrors `_is_epoch_zero`'s `str`-vs-`int` handling: returns `value`
    unchanged for a Python `int`; for a `str`, returns `int(value.strip())`
    if that parses without raising; otherwise (including any other type)
    returns `None`. A `None` result means "cannot be safely compared as an
    epoch integer" -- callers must treat that as "skip this check", never
    raise from the coercion itself.
    """
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _parse_retry_after(response) -> Optional[float]:
    """Parse a `Retry-After` header's delay-in-seconds form, if present.

    Only the integer delay-in-seconds form is parsed; an HTTP-date value is
    treated as absent (`None`), since it is not the form Loki's rate-limit
    middleware sends in practice. A parsed value that is non-positive
    (<= 0) is also treated as absent, the same as an unparseable value --
    it is not a usable delay, and passing it through would let a
    server-supplied negative value reach a caller's sleep/wait call.
    """
    header_value = response.headers.get("Retry-After")
    if header_value is None:
        return None
    try:
        parsed = float(int(header_value))
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


class LogAPI(APIResourse):
    def _workload_log_param(self) -> str:
        """The query key the shared ``/logs*`` routes use for a deployment/endpoint.

        When the new deployment API is enabled the workload is a LeptonEndpoint,
        and the backend keys its logs under ``endpoint=`` (a distinct branch in
        ``api-server/httpapi/log/handler_log.go``); the legacy ``deployment=``
        key resolves a /deployments resource that does not exist in that mode, so
        the query would silently return no logs. Off, the legacy key is correct.
        """
        return "endpoint" if self._client.new_deployment_api_enabled else "deployment"

    def get_log_time_series(
        self,
        name_or_deployment: Union[str, LeptonDeployment] = None,
        name_or_job: Union[str, LeptonJob] = None,
        replica: Union[str, Replica] = None,
        start: int = None,
        end: int = None,
        interval_ms: int = None,
        limit: int = None,
        q: str = "",
        job_query_mode: str = LeptonJobQueryMode.AliveAndArchive.value,
        direction: str = "backward",
    ):
        """
        Call /logs/timeseries to retrieve aggregated time series for logs.

        Args:
            name_or_deployment: Deployment name or object
            name_or_job: Job id or object
            replica: Replica id or object
            start: Start timestamp (ns)
            end: End timestamp (ns)
            interval_ms: Bucket interval in milliseconds
            limit: Max number of data points
            q: Query string
            job_query_mode: alive_and_archive | alive_only | archive_only (backend specific)
            direction: forward | backward
        Returns:
            JSON-decoded response from the API
        """

        query_kwargs = {}

        if start is not None:
            query_kwargs["start"] = start
        if end is not None:
            query_kwargs["end"] = end
        if interval_ms is not None:
            query_kwargs["interval_ms"] = interval_ms
        if limit is not None:
            query_kwargs["limit"] = limit
        if q is not None:
            query_kwargs["q"] = q
        if job_query_mode:
            query_kwargs["job_query_mode"] = job_query_mode
        if direction:
            query_kwargs["direction"] = direction

        if name_or_deployment:
            deployment_id = (
                name_or_deployment
                if isinstance(name_or_deployment, str)
                else name_or_deployment.metadata.id_
            )
            query_kwargs[self._workload_log_param()] = deployment_id
        elif name_or_job:
            job_id = (
                name_or_job
                if isinstance(name_or_job, str)
                else name_or_job.metadata.id_
            )
            query_kwargs["job"] = job_id

        if replica:
            replica_id = replica if isinstance(replica, str) else replica.metadata.id_
            query_kwargs["replica"] = replica_id

        response = self._get(
            "/logs/timeseries",
            params=query_kwargs,
        )
        if not response.ok:
            raise RuntimeError(
                f"API call failed with status code {response.status_code}. Details:"
                f" {response.text}"
            )
        return response.json()

    def get_log(
        self,
        name_or_deployment: Union[str, LeptonDeployment] = None,
        name_or_job: Union[str, LeptonJob] = None,
        replica: Union[str, Replica] = None,
        job_history_name: str = None,
        start: str = None,
        end: str = None,
        limit: int = 5000,
        q: str = "",
        job_query_mode: str = "alive_and_archive",
        direction: str = "backward",
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Args:
            timeout: optional per-request timeout in seconds, passed through
                to the underlying HTTP GET. When omitted (the default),
                behavior is unchanged: the client's normal request timeout
                (`self._client._timeout`, 120s) applies. Existing callers
                that do not pass `timeout` are unaffected.
        """
        query_kwargs = {}
        # `is not None` (not truthiness) checks distinguish "not provided"
        # from a literal 0. A literal 0 is rejected below rather than
        # forwarded, since the /logs API cannot distinguish it from omitted.
        if _is_epoch_zero(start) or _is_epoch_zero(end):
            raise RuntimeError(
                "start=0/end=0 cannot be distinguished from an omitted"
                " start/end by the /logs API - pass a non-zero epoch"
                " timestamp, or omit both start and end for the default"
                " range."
            )
        start_int = _to_epoch_int(start)
        end_int = _to_epoch_int(end)
        if (start_int is not None and start_int < 0) or (
            end_int is not None and end_int < 0
        ):
            raise RuntimeError("start/end must be a non-negative epoch timestamp")
        if start is not None and end is not None:
            if start_int is not None and end_int is not None and end_int <= start_int:
                raise RuntimeError("end must be after start for historical logs")
            query_kwargs["start"] = start
            query_kwargs["end"] = end
            query_kwargs["timestamps"] = True
            query_kwargs["direction"] = direction
            query_kwargs["limit"] = limit
            query_kwargs["q"] = q
            if job_query_mode:
                query_kwargs["job_query_mode"] = job_query_mode
        elif (start is not None) != (end is not None):
            raise RuntimeError(
                "For historical logs, both start or end must be specified"
            )

        if name_or_deployment:
            deployment_id = (
                name_or_deployment
                if isinstance(name_or_deployment, str)
                else name_or_deployment.metadata.id_
            )
            query_kwargs[self._workload_log_param()] = deployment_id

        elif name_or_job:
            job_id = (
                name_or_job
                if isinstance(name_or_job, str)
                else name_or_job.metadata.id_
            )

            query_kwargs["job"] = job_id

        elif job_history_name:
            query_kwargs["job_history_name"] = job_history_name

        if replica:
            replica_id = replica if isinstance(replica, str) else replica.metadata.id_
            query_kwargs["replica"] = replica_id

        get_kwargs = {"params": query_kwargs}
        if timeout is not None:
            get_kwargs["timeout"] = timeout
        response = self._get("/logs", **get_kwargs)
        if not response.ok:
            raise LogAPIError(
                f"API call failed with status code {response.status_code}. Details:"
                f" {response.text}",
                status_code=response.status_code,
                retry_after=_parse_retry_after(response),
            )
        return response.json()
