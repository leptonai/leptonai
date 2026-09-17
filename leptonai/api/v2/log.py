import codecs
from typing import Any, Dict, Iterator, Optional, Union

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
    """Access shared workload logs through ``APIClient().log``.

    ``get_log()`` returns one historical JSON response or a live text iterator.
    ``get_log_time_series()`` returns aggregated log time series as JSON.
    Workload selectors are mutually exclusive; resource-specific filters apply
    to the selected workload. Authorization and log retention are enforced by
    the server.

    These SDK methods do not automatically paginate, retry requests, or throttle
    request frequency. Callers making repeated queries must handle rate limits;
    an HTTP 429 is raised as ``LogAPIError`` with ``status_code`` and
    ``retry_after`` attributes.
    The CLI's historical-query retry behavior is separate.
    """

    def _workload_log_param(self) -> str:
        """The query key the shared ``/logs*`` routes use for a deployment/endpoint.

        When the new deployment API is enabled the workload is a LeptonEndpoint,
        and the backend keys its logs under ``endpoint=`` (a distinct branch in
        ``api-server/httpapi/log/handler_log.go``); the legacy ``deployment=``
        key resolves a /deployments resource that does not exist in that mode, so
        the query would silently return no logs. Off, the legacy key is correct.
        """
        return "endpoint" if self._client.new_deployment_api_enabled else "deployment"

    def _query_params(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """Build query parameters from locals(), excluding client-only options."""
        owners = {
            "name_or_deployment": "deployment",
            "name_or_endpoint": "endpoint",
            "name_or_job": "job",
            "name_or_dynamo": "dynamo_graph_deployment",
            "name_or_dev_pod": "dev_pod",
            "name_or_ray_cluster": "ray_cluster",
            "slurm_cluster": "slurm_cluster",
        }
        if sum(bool(values.get(key)) for key in owners) > 1:
            raise ValueError("Specify only one workload for a log query.")
        if values.get("component") and not (
            values.get("name_or_endpoint") or values.get("name_or_deployment")
        ):
            raise ValueError("component requires an endpoint.")
        if any(
            values.get(key) for key in ("ray_job_id", "ray_component", "ray_node_id")
        ) and not values.get("name_or_ray_cluster"):
            raise ValueError("Ray filters require name_or_ray_cluster.")
        if any(values.get(key) for key in values if key.startswith("slurm_")) and not (
            values.get("slurm_namespace") and values.get("slurm_cluster")
        ):
            raise ValueError("Slurm logs require slurm_namespace and slurm_cluster.")
        if values.get("job_history_name") and not values.get("name_or_job"):
            raise ValueError("job_history_name requires name_or_job.")
        if values.get("direction") not in (None, "forward", "backward"):
            raise ValueError("direction must be forward or backward.")
        if values.get("job_query_mode") not in (
            None,
            "",
            "alive_only",
            "archive_only",
            "alive_and_archive",
        ):
            raise ValueError("Invalid job_query_mode.")
        for key in ("limit", "interval_ms"):
            if values.get(key) is not None and values[key] <= 0:
                raise ValueError(f"{key} must be positive.")
        params = {}
        for key, value in values.items():
            if key in ("self", "stream", "timeout") or value is None:
                continue
            if key in owners:
                if not value:
                    continue
                if key == "name_or_deployment":
                    key = self._workload_log_param()
                else:
                    key = owners[key]
                if not isinstance(value, str):
                    value = value.metadata.id_ or value.metadata.name
            elif key == "replica" and not isinstance(value, str):
                value = value.metadata.id_
            if isinstance(value, bool):
                value = str(value).lower()
            params[key] = value
        return params

    @staticmethod
    def _raise_log_error(response):
        if not response.ok:
            raise LogAPIError(
                f"API call failed with status code {response.status_code}. Details:"
                f" {response.text}",
                status_code=response.status_code,
                retry_after=_parse_retry_after(response),
            )

    @staticmethod
    def _validate_time_bounds(start, end):
        if _is_epoch_zero(start) or _is_epoch_zero(end):
            raise RuntimeError(
                "start=0/end=0 cannot be distinguished from an omitted"
                " start/end by the /logs API - pass a non-zero epoch"
                " timestamp, or omit both start and end for the default range."
            )
        start_int, end_int = _to_epoch_int(start), _to_epoch_int(end)
        if (start_int is not None and start_int < 0) or (
            end_int is not None and end_int < 0
        ):
            raise RuntimeError("start/end must be a non-negative epoch timestamp")
        if start_int is not None and end_int is not None and end_int <= start_int:
            raise RuntimeError("end must be after start for historical logs")

    def _read_json(self, path, params, timeout):
        """Read one JSON response and close it, rejecting live-text responses."""
        # Read headers first even for JSON, so an unexpected live response never
        # buffers an unbounded body before we can report the mode mismatch.
        kwargs = {"timeout": timeout} if timeout is not None else {}
        response = self._get(path, params=params, stream=True, **kwargs)
        try:
            self._raise_log_error(response)
            if (
                response.headers.get("Content-Type", "")
                .split(";", 1)[0]
                .strip()
                .lower()
                == "text/plain"
            ):
                raise RuntimeError(
                    "The server returned live logs; use stream=True with replica and an"
                    " empty q."
                )
            return response.json()
        finally:
            response.close()

    def _stream_log(self, params, timeout) -> Iterator[str]:
        """Yield decoded live chunks; close the response on exit or cancellation."""
        response = self._get("/logs", params=params, stream=True, timeout=timeout)
        try:
            self._raise_log_error(response)
            if (
                response.headers.get("Content-Type", "")
                .split(";", 1)[0]
                .strip()
                .lower()
                == "application/json"
            ):
                raise RuntimeError(
                    "Expected live log text, but the server returned JSON."
                )
            decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
            for chunk in response.iter_content(chunk_size=None):
                text = decoder.decode(chunk)
                if text:
                    yield text
            remaining = decoder.decode(b"", final=True)
            if remaining:
                yield remaining
        finally:
            response.close()

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
        name_or_dynamo: Optional[str] = None,
        dynamo_service: str = None,
        *,
        level: Optional[str] = None,
        name_or_endpoint: Optional[str] = None,
        component: Optional[str] = None,
        name_or_dev_pod: Optional[str] = None,
        name_or_ray_cluster: Optional[str] = None,
        ray_job_id: Optional[str] = None,
        ray_component: Optional[str] = None,
        ray_node_id: Optional[str] = None,
        slurm_namespace: Optional[str] = None,
        slurm_cluster: Optional[str] = None,
        slurm_host: Optional[str] = None,
        slurm_node: Optional[str] = None,
        slurm_job: Optional[str] = None,
        slurm_step: Optional[str] = None,
        slurm_attempt: Optional[str] = None,
        slurm_log_type: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Retrieve aggregated log time series from ``GET /logs/timeseries``.

        Returns a single decoded JSON response. This method never returns a
        live iterator, including when ``replica`` is supplied. At most one
        workload selector may be specified. Time bounds use Unix nanoseconds;
        CLI time expressions such as ``"today"`` are not parsed by the SDK.

        Args:
            name_or_deployment: Deployment name or object. Uses the ``endpoint``
                query key when the workspace enables the new deployment API;
                otherwise uses ``deployment``.
            name_or_job: Job ID or object. Mutually exclusive with other
                workload selectors.
            replica: Replica ID or object to filter within the workload.
                Not supported with ``name_or_dev_pod`` on this route.
            start: Start timestamp in Unix nanoseconds. May be supplied without
                ``end``. ``None`` omits the parameter; zero uses server defaults.
            end: End timestamp in Unix nanoseconds. May be supplied without
                ``start``. ``None`` omits the parameter; zero uses server defaults.
            interval_ms: Positive aggregation interval in milliseconds. If
                omitted, the server chooses an interval based on the time range.
                The server also enforces a minimum interval for that range.
            limit: Positive maximum number of data points requested. ``None``
                leaves the limit to the server (currently 200).
            q: Literal text filter. Defaults to an empty string for no text
                filter; this is not a raw LogQL expression.
            job_query_mode: Job lookup scope: ``"alive_only"``,
                ``"archive_only"``, or ``"alive_and_archive"`` (default).
            direction: Retrieval direction, ``"forward"`` or ``"backward"``
                (default). The SDK preserves the server's response ordering.
            name_or_dynamo: Dynamo graph deployment ID. Sent as
                ``dynamo_graph_deployment``.
            dynamo_service: Unsupported legacy parameter. A nonempty value
                raises ``ValueError`` because the backend ignores this filter.
            level: Comma-separated log levels, for example ``"error,warn"``.
                Omit to query all levels. The server validates the level names.
            name_or_endpoint: Explicit endpoint ID, sent as ``endpoint`` without
                selecting a query key from the workspace API flag.
            component: Endpoint component name. Requires ``name_or_endpoint``
                or an endpoint selected through ``name_or_deployment``.
            name_or_dev_pod: DevPod ID, sent as ``dev_pod``. Requires the new
                deployment API to be enabled in the workspace.
            name_or_ray_cluster: Ray cluster ID, sent as ``ray_cluster``.
            ray_job_id: Ray job ID filter; requires ``name_or_ray_cluster``.
            ray_component: Ray component filter; requires
                ``name_or_ray_cluster``.
            ray_node_id: Ray node ID filter; requires ``name_or_ray_cluster``.
            slurm_namespace: Slurm cluster namespace. Must be supplied together
                with ``slurm_cluster`` when using any Slurm filter.
            slurm_cluster: Slurm cluster name. Mutually exclusive with other
                workload selectors; requires ``slurm_namespace``.
            slurm_host: Host of a Slurm log entry. Requires the Slurm selector.
            slurm_node: Slurm job task node. Requires the Slurm selector.
            slurm_job: Slurm job ID. Requires the Slurm selector.
            slurm_step: Slurm step ID. Requires the Slurm selector.
            slurm_attempt: Slurm requeue attempt. Requires the Slurm selector.
            slurm_log_type: Slurm log type. Requires the Slurm selector.
            timeout: HTTP connect/read timeout in seconds. ``None`` uses the
                API client's default. This is not a total request deadline.

        Returns:
            The backend's JSON response as a dictionary, including its
            ``data.result`` time series. No model conversion or pagination
            is performed.

        Raises:
            ValueError: Workload selectors conflict, a filter lacks its required
                selector, an option value is invalid, or an unsupported filter
                is supplied (``dynamo_service`` or a DevPod replica).
            LogAPIError: The server returns a non-success HTTP status.
                ``status_code`` carries the status; ``retry_after`` carries a
                positive Retry-After delay in seconds, when supplied.
            RuntimeError: The server returns live text instead of JSON.
            requests.RequestException: A network, timeout, or JSON decoding
                error occurs.

        Examples:
            Query one-minute buckets for the last hour::

                import time
                from leptonai.api.v2.client import APIClient

                client = APIClient()
                end = time.time_ns()
                series = client.log.get_log_time_series(
                    name_or_deployment="my-endpoint",
                    start=end - 3600 * 1_000_000_000,
                    end=end,
                    interval_ms=60_000,
                    level="error,warn",
                )
        """
        if dynamo_service:
            raise ValueError("dynamo_service is not supported by /logs/timeseries.")
        if name_or_dev_pod and replica:
            raise ValueError(
                "/logs/timeseries does not support replica filtering for DevPods."
            )
        params = self._query_params(locals())
        return self._read_json("/logs/timeseries", params, timeout)

    def get_log(
        self,
        name_or_deployment: Union[str, LeptonDeployment] = None,
        name_or_job: Union[str, LeptonJob] = None,
        replica: Union[str, Replica] = None,
        job_history_name: str = None,
        start: Union[int, str] = None,
        end: Union[int, str] = None,
        limit: int = 5000,
        q: str = "",
        job_query_mode: str = "alive_and_archive",
        direction: str = "backward",
        timeout: Optional[float] = None,
        *,
        name_or_dynamo: Optional[str] = None,
        dynamo_service: str = None,
        stream: bool = False,
        timestamps: bool = False,
        level: Optional[str] = None,
        name_or_endpoint: Optional[str] = None,
        component: Optional[str] = None,
        name_or_dev_pod: Optional[str] = None,
        name_or_ray_cluster: Optional[str] = None,
        ray_job_id: Optional[str] = None,
        ray_component: Optional[str] = None,
        ray_node_id: Optional[str] = None,
        slurm_namespace: Optional[str] = None,
        slurm_cluster: Optional[str] = None,
        slurm_host: Optional[str] = None,
        slurm_node: Optional[str] = None,
        slurm_job: Optional[str] = None,
        slurm_step: Optional[str] = None,
        slurm_attempt: Optional[str] = None,
        slurm_log_type: Optional[str] = None,
    ) -> Union[Dict[str, Any], Iterator[str]]:
        """Retrieve historical logs or stream live replica logs from ``GET /logs``.

        With ``stream=False`` (default), sends ``q`` even when it is empty and
        returns one decoded JSON response. With ``stream=True``, omits ``q``
        entirely, even if supplied, and returns an iterator of text chunks.
        An empty ``q=`` and an absent ``q`` select different response modes on
        deployed servers; HTTP streaming alone does not select live logs.

        At most one workload selector may be specified. ``replica`` optionally
        narrows historical queries and is required for live streaming. Slurm
        queries only support historical mode. The server fixes the initial live
        tail at up to 10,000 lines; this method cannot configure that tail.

        Args:
            name_or_deployment: Deployment name or object. Uses the ``endpoint``
                query key when the workspace enables the new deployment API;
                otherwise uses ``deployment``.
            name_or_job: Job ID or object. Mutually exclusive with other
                workload selectors.
            replica: Replica ID or object. Optional for historical queries;
                required when ``stream=True``.
            job_history_name: Historical job-generation override. Requires
                ``name_or_job`` and must belong to that job. Not supported in
                live mode; ownership is validated by the server.
            start: Historical start timestamp in Unix nanoseconds, as an integer
                or decimal string. May be supplied without ``end``. ``None``
                omits it; zero is rejected because the server treats it as
                omitted. Human-readable dates and CLI time expressions such as
                ``"today"`` are not parsed here.
            end: Historical end timestamp in Unix nanoseconds, as an integer or
                decimal string. May be supplied without ``start``. ``None``
                omits it; zero is rejected because the server treats it as omitted.
            limit: Positive maximum number of historical log entries, default
                5000. No automatic pagination occurs. In live mode, leave this
                at its default: other values are rejected, and no limit is sent.
            q: Literal historical text filter, not raw LogQL. Omitted or ``None``
                becomes ``q=""`` on historical requests. Ignored and omitted
                from the request when ``stream=True``.
            job_query_mode: Job lookup scope: ``"alive_only"``,
                ``"archive_only"``, or ``"alive_and_archive"`` (default).
            name_or_dynamo: Dynamo graph deployment ID. Sent as
                ``dynamo_graph_deployment``.
            dynamo_service: Legacy parameter retained for compatibility. The
                current shared logs backend ignores it; it does not filter
                results by Dynamo service.
            stream: If true, return a lazy iterator of live UTF-8 text chunks.
                The ``/logs`` request starts on iteration. Requires ``replica``
                and a non-Slurm workload; time bounds, ``job_history_name``,
                ``level``, and non-default ``limit``/``direction`` are rejected.
            timestamps: Prefix live log lines with server timestamps when true.
                Defaults to false. Ignored by the server for historical queries.
            direction: Historical retrieval direction: ``"forward"`` for
                earlier entries first, or ``"backward"`` (default) for later
                entries first. Leave at its default in live mode; it is not sent.
            level: Comma-separated historical log levels, for example
                ``"error,warn"``. Omit to query all levels. Not supported in
                live mode; the server validates level names.
            name_or_endpoint: Explicit endpoint ID, sent as ``endpoint`` without
                selecting a query key from the workspace API flag.
            component: Endpoint component name. Requires ``name_or_endpoint``
                or an endpoint selected through ``name_or_deployment``. Applies
                to historical queries; live mode targets the specified replica.
            name_or_dev_pod: DevPod ID, sent as ``dev_pod``. Requires the new
                deployment API to be enabled in the workspace.
            name_or_ray_cluster: Ray cluster ID, sent as ``ray_cluster``.
            ray_job_id: Historical Ray job ID filter; requires
                ``name_or_ray_cluster``. Live mode targets the replica directly.
            ray_component: Historical Ray component filter; requires
                ``name_or_ray_cluster``. Live mode targets the replica directly.
            ray_node_id: Historical Ray node ID filter; requires
                ``name_or_ray_cluster``. Live mode targets the replica directly.
            slurm_namespace: Slurm cluster namespace. Must be supplied together
                with ``slurm_cluster`` when using any Slurm filter.
            slurm_cluster: Slurm cluster name. Mutually exclusive with other
                workload selectors; requires ``slurm_namespace``.
            slurm_host: Host of a Slurm log entry. Requires the Slurm selector.
            slurm_node: Slurm job task node. Requires the Slurm selector.
            slurm_job: Slurm job ID. Requires the Slurm selector.
            slurm_step: Slurm step ID. Requires the Slurm selector.
            slurm_attempt: Slurm requeue attempt. Requires the Slurm selector.
            slurm_log_type: Slurm log type. Requires the Slurm selector.
            timeout: HTTP connect/read timeout in seconds, not a total stream
                duration. ``None`` uses the client default for historical
                queries and disables timeouts for live streams.

        Returns:
            A dictionary containing the historical JSON response when
            ``stream=False``. Entries remain grouped in ``data.result`` with
            each group's ``values`` containing timestamp/text pairs; the SDK
            does not merge, sort, or paginate them.

            An ``Iterator[str]`` when ``stream=True``. Chunks are decoded
            incrementally as UTF-8 and may contain partial or multiple lines.
            Invalid UTF-8 is replaced. Close the iterator when stopping early
            to release the connection, for example with ``contextlib.closing``.
            Exhaustion or an iteration error also closes the response.

        Raises:
            ValueError: Workload selectors conflict, a filter lacks its required
                selector, an option value is invalid, or live-mode requirements
                are violated. These checks occur before returning the iterator.
            LogAPIError: The server returns a non-success HTTP status.
                ``status_code`` carries the status; ``retry_after`` carries a
                positive Retry-After delay in seconds, when supplied.
            RuntimeError: Time bounds are zero, negative, or not ascending, or
                the response mode differs from the requested mode
                (JSON for live logs, or live text for historical logs).
            requests.RequestException: A network, timeout, or JSON decoding
                error occurs. In live mode, request/response errors occur during
                iteration, and the SDK does not reconnect automatically.

        Examples:
            Fetch a single page of unfiltered replica history::

                from leptonai.api.v2.client import APIClient

                client = APIClient()
                logs = client.log.get_log(
                    name_or_deployment="my-endpoint",
                    replica="my-replica",
                    limit=100,
                )

            Follow live logs and close the connection when leaving the block::

                from contextlib import closing

                with closing(client.log.get_log(
                    name_or_deployment="my-endpoint",
                    replica="my-replica",
                    stream=True,
                    timestamps=True,
                )) as chunks:
                    for chunk in chunks:
                        print(chunk, end="", flush=True)
        """
        if not stream:
            self._validate_time_bounds(start, end)
        params = self._query_params(locals())
        if stream:
            if not replica or slurm_cluster:
                raise ValueError("Live logs require replica and a non-Slurm workload.")
            if (
                start is not None
                or end is not None
                or level
                or limit != 5000
                or direction != "backward"
                or job_history_name
            ):
                raise ValueError(
                    "Live logs do not support start/end, level, limit, direction, or"
                    " job_history_name."
                )
            # Omit q entirely: deployed servers can interpret even q= as a
            # historical query. stream=True alone only controls HTTP buffering.
            for key in ("q", "start", "end", "limit", "direction", "level"):
                params.pop(key, None)
            return self._stream_log(params, timeout)
        # A present q (including q=) selects historical queries on the server.
        params["q"] = q if q is not None else ""
        return self._read_json("/logs", params, timeout)
