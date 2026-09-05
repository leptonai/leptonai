"""Shared test scaffolding for the adaptive log-fetch test suites
(`test_log_cli.py`, `test_log_adaptive_scheduler.py`,
`test_log_adaptive_worker.py`, `test_log_adaptive_output.py`): Loki response
construction, fake `APIClient`/`client.log` factories, and small
thread-timing helpers used across these files' concurrency/backoff tests.

Test ownership, going forward: worker handles page/retry; scheduler
handles queue/order; output handles sinks; CLI handles wiring.
"""

import threading
import time
from unittest.mock import MagicMock

# Captured before any test patches `time.sleep` -- `time` here is the same
# stdlib module object every other test module imports, so patching one
# attribute patches it process-wide. Anything that needs to actually sleep a
# bounded real duration from inside a patched `time.sleep` side_effect must
# go through this reference to avoid infinite self-recursion.
_REAL_SLEEP = time.sleep


def pad_entries(n, lo, hi, prefix):
    """n distinct-line entries with timestamps cycling through [lo, hi],
    guaranteeing at least one entry at exactly `lo` and one at exactly `hi`
    (so callers can rely on min/max of the resulting saturated page)."""
    span = hi - lo
    entries = [(lo + (i % (span + 1)), f"{prefix}{i}", {}) for i in range(n - 1)]
    entries.append((hi, f"{prefix}-max", {}))
    return entries


def loki_response(entries):
    """Build a Loki query_range-shaped payload from (ts_ns, line, stream) tuples."""
    by_stream = {}
    for ts, line, stream in entries:
        by_stream.setdefault(tuple(sorted(stream.items())), []).append([str(ts), line])
    result = [
        {"stream": dict(stream_items), "values": values}
        for stream_items, values in by_stream.items()
    ]
    return {"data": {"result": result}}


class RecordingFakeLogAPI:
    """Fake `client.log` recording every `get_log` call and its `direction`.

    `script` maps (start, end) -> either a scripted response dict, an
    Exception instance (raised once) or a list of such (consumed in order,
    last one repeats).
    """

    def __init__(self, script):
        self.script = script
        self.calls = []
        self._call_counts = {}
        self.lock = threading.Lock()

    def get_log(self, **kwargs):
        key = (kwargs.get("start"), kwargs.get("end"))
        with self.lock:
            self.calls.append(dict(kwargs))
            self._call_counts[key] = self._call_counts.get(key, 0) + 1
            n = self._call_counts[key]

        outcome = self.script.get(key)
        if isinstance(outcome, list):
            outcome = outcome[min(n - 1, len(outcome) - 1)]
        if isinstance(outcome, Exception):
            raise outcome
        if outcome is None:
            return {"data": {"result": []}}
        return outcome


class FakeHTTPResponse:
    def __init__(self, payload, ok=True, status_code=200, text=""):
        self.ok = ok
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = {}

    def json(self):
        return self._payload


class RealLogAPIHTTPClient:
    """Fake HTTP transport for a real `LogAPI` instance -- lets a test drive
    `LogAPI`'s own request/response parsing (e.g. `Retry-After` header
    handling, precondition rejection) end to end, instead of constructing an
    already-parsed `LogAPIError` by hand."""

    def __init__(self):
        self.new_deployment_api_enabled = False
        self._get = MagicMock(return_value=FakeHTTPResponse({"data": {"result": []}}))
        self._post = MagicMock()
        self._put = MagicMock()
        self._patch = MagicMock()
        self._delete = MagicMock()
        self._head = MagicMock()


class FakeDeploymentAPI:
    def get(self, name):
        return None

    def get_replicas(self, name):
        return []


def make_client_class(fake_log_api):
    """Build a fake `APIClient` class exposing `.log` and a no-op
    `.deployment` (unused by scheduler-layer tests, but required by the
    CLI's own pre-dispatch deployment lookup)."""

    class _Client:
        last_instance = None

        def __init__(self, *args, **kwargs):
            self.log = fake_log_api
            self.deployment = FakeDeploymentAPI()
            _Client.last_instance = self

    return _Client


class InFlightTracker:
    """Tracks the max number of concurrently-in-flight fake get_log calls."""

    def __init__(self):
        self.lock = threading.Lock()
        self.current = 0
        self.max_seen = 0

    def enter(self):
        with self.lock:
            self.current += 1
            self.max_seen = max(self.max_seen, self.current)

    def leave(self):
        with self.lock:
            self.current -= 1


def two_unit_cancellation_fixture():
    """Shared (frontier, blocked) unit pair for sink-cancellation tests:
    UNIT_LOW resolves once UNIT_BLOCK has genuinely started (via the
    returned `block_started` event), triggering cancellation while
    UNIT_BLOCK is still in flight. Returns
    (UNIT_LOW, UNIT_BLOCK, block_duration, block_started)."""
    return (0, 5), (100, 200), 0.2, threading.Event()


def wait_for_quiescent_threads(timeout=2.0):
    """Block until only the main thread remains (or `timeout` elapses).

    `time.sleep` is a single process-wide stdlib attribute, so patching it
    (as every 429/backoff test does) affects *every* thread in the process,
    not just the one under test. A worker thread from a just-finished prior
    test that hasn't fully wound down yet would then have its own
    `time.sleep` call routed into the *next* test's recorder, inflating call
    counts. Call this before installing a `time.sleep` patch in tests that
    assert an exact concurrent call count, to guarantee no straggler thread
    is still in flight.
    """
    start = time.monotonic()
    while threading.active_count() > 1 and time.monotonic() - start < timeout:
        _REAL_SLEEP(0.01)
