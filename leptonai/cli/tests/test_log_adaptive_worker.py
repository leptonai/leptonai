"""Unit tests for the single-request-cycle building blocks of adaptive log
retrieval: `_parse_log_entries` (response parsing/validation/page-limit
capping), `LogEntry` identity, and `_fetch_log_unit` (one HTTP
request/response cycle, including retry/backoff and `Retry-After` handling).

None of these need a `ThreadPoolExecutor` or an `_AdaptiveLogScheduler`
fixture -- scheduler-owned state (pending/active/buffer, watermark, split
decisions, admission, output coordination) lives in
`test_log_adaptive_scheduler.py`; output/sink formatting lives in
`test_log_adaptive_output.py`.
"""

import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai, matching
# the existing CLI test suite convention (test_job_cli.py).
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import heapq
import threading
import time
import unittest
from unittest.mock import patch

from leptonai.api.v2.log import LogAPI, LogAPIError
from leptonai.cli import log as log_mod
from leptonai.cli.log import (
    LogEntry,
    _ADAPTIVE_RETRY_BASE_DELAY_SEC,
    _ADAPTIVE_RETRY_MAX_ATTEMPTS,
    _fetch_log_unit,
    _MalformedLogResponseError,
    _parse_log_entries,
    _RateLimitSignal,
)
from leptonai.cli.tests._log_test_helpers import (
    FakeHTTPResponse as _FakeHTTPResponse,
    RealLogAPIHTTPClient as _RealLogAPIHTTPClient,
    RecordingFakeLogAPI as _RecordingFakeLogAPI,
    loki_response as _loki_response,
    make_client_class as _make_client_class,
)


class TestLogEntryDedupKey(unittest.TestCase):
    def test_identical_entries_are_equal_and_hash_equal(self):
        a = LogEntry((("pod", "p1"),), 100, "hello", ())
        b = LogEntry((("pod", "p1"),), 100, "hello", ())
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))

    def test_different_stream_labels_are_not_equal(self):
        a = LogEntry((("pod", "p1"),), 100, "hello", ())
        b = LogEntry((("pod", "p2"),), 100, "hello", ())
        self.assertNotEqual(a, b)

    def test_different_metadata_are_not_equal(self):
        a = LogEntry((("pod", "p1"),), 100, "hello", ())
        b = LogEntry((("pod", "p1"),), 100, "hello", (("k", "v"),))
        self.assertNotEqual(a, b)


class TestFetchLogUnit(unittest.TestCase):
    def test_calls_get_log_with_the_bounded_adaptive_fetch_timeout(self):
        # `_fetch_log_unit` passes a specific, bounded timeout
        # (`_ADAPTIVE_FETCH_TIMEOUT_SEC`, shorter than the client's normal
        # 120s default) to `get_log`, so a sink failure that triggers
        # cancellation while a worker is mid-HTTP-request bounds shutdown
        # to a known, short duration instead of silently inheriting 120s.
        fake = _RecordingFakeLogAPI({(0, 100): _loki_response([(1, "a", {})])})
        with patch.object(log_mod, "APIClient", _make_client_class(fake)):
            _fetch_log_unit(None, "job-1", None, None, "", 0, 100, limit=5000)
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.calls[0]["timeout"], log_mod._ADAPTIVE_FETCH_TIMEOUT_SEC)
        self.assertLess(log_mod._ADAPTIVE_FETCH_TIMEOUT_SEC, 120)

    def test_non_saturated_returns_all_entries_as_final(self):
        entries = [(3, "c", {}), (1, "a", {}), (2, "b", {})]
        fake = _RecordingFakeLogAPI({(0, 100): _loki_response(entries)})
        with patch.object(log_mod, "APIClient", _make_client_class(fake)):
            result = _fetch_log_unit(None, "job-1", None, None, "", 0, 100, limit=5000)
        self.assertFalse(result.saturated)
        self.assertFalse(result.failed)
        self.assertEqual(len(result.entries), 3)
        # Sorted ascending by timestamp regardless of Loki response order.
        self.assertEqual([e.timestamp_ns for e in result.entries], [1, 2, 3])
        self.assertEqual(result.min_ts, 1)
        self.assertEqual(result.max_ts, 3)
        self.assertEqual(fake.calls[0]["direction"], "forward")

    def test_saturated_when_page_hits_limit(self):
        entries = [(i, f"line-{i}", {}) for i in range(5)]
        fake = _RecordingFakeLogAPI({(0, 100): _loki_response(entries)})
        with patch.object(log_mod, "APIClient", _make_client_class(fake)):
            result = _fetch_log_unit(None, "job-1", None, None, "", 0, 100, limit=5)
        self.assertTrue(result.saturated)
        self.assertEqual(len(result.entries), 5)

    def test_exhausted_retries_report_failed_without_raising(self):
        fake = _RecordingFakeLogAPI({(0, 100): RuntimeError("boom")})
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.time, "sleep", return_value=None) as mock_sleep,
        ):
            result = _fetch_log_unit(None, "job-1", None, None, "", 0, 100, limit=5000)
        self.assertTrue(result.failed)
        self.assertEqual(result.entries, [])
        self.assertIsNone(result.min_ts)
        self.assertIsNone(result.max_ts)
        self.assertEqual(len(fake.calls), 5)
        self.assertEqual(mock_sleep.call_count, 4)

    def test_transient_failure_recovers_within_retry_budget(self):
        fake = _RecordingFakeLogAPI({
            (0, 100): [
                RuntimeError("e1"),
                RuntimeError("e2"),
                RuntimeError("e3"),
                _loki_response([(1, "ok", {})]),
            ]
        })
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.time, "sleep", return_value=None),
        ):
            result = _fetch_log_unit(None, "job-1", None, None, "", 0, 100, limit=5000)
        self.assertFalse(result.failed)
        self.assertEqual(len(result.entries), 1)
        self.assertEqual(len(fake.calls), 4)

    def test_cancelled_before_first_attempt_makes_no_request(self):
        fake = _RecordingFakeLogAPI({(0, 100): _loki_response([(1, "a", {})])})
        cancelled = threading.Event()
        cancelled.set()
        with patch.object(log_mod, "APIClient", _make_client_class(fake)):
            result = _fetch_log_unit(
                None, "job-1", None, None, "", 0, 100, limit=5000, cancelled=cancelled
            )
        self.assertTrue(result.failed)
        self.assertEqual(len(fake.calls), 0)


class TestRateLimitSignal(unittest.TestCase):
    """Shared 429 signal semantics."""

    def test_inactive_by_default(self):
        self.assertFalse(_RateLimitSignal().active())

    def test_active_until_cooldown_elapses(self):
        signal = _RateLimitSignal()
        signal.signal(0.05)
        self.assertTrue(signal.active())
        time.sleep(0.08)
        self.assertFalse(signal.active())

    def test_signal_only_extends_deadline_forward_never_backward(self):
        signal = _RateLimitSignal()
        signal.signal(0.2)
        signal.signal(0.05)  # shorter cooldown must not shorten the longer one
        time.sleep(0.1)
        self.assertTrue(signal.active())


class TestSharedCooldownMatchesWorkersOwnDelay(unittest.TestCase):
    """Drives `_fetch_log_unit` directly, never through Click/CliRunner.

    On a no-Retry-After-header 429, `_fetch_log_unit` signals the
    shared `_RateLimitSignal` with `cooldown = delay` -- the same jittered
    backoff value the worker itself is about to sleep for -- instead of a
    fixed default cooldown. Directly drives two simulated workers (via a
    shared `_RateLimitSignal` and controlled `random.uniform`) with
    different jittered delays and asserts the signal's active-until
    deadline reflects the larger of the two, not a fixed constant.
    """

    def test_cooldown_reflects_the_larger_of_two_workers_own_jittered_delays(self):
        S, E = 0, 100
        rate_limit_signal = _RateLimitSignal()
        cancelled = threading.Event()

        fake_a = _RecordingFakeLogAPI({
            (S, E): [
                LogAPIError("rate limited", 429, retry_after=None),
                _loki_response([(S + 1, "a", {})]),
            ]
        })
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake_a)),
            patch.object(log_mod.random, "uniform", return_value=1.0),
            patch.object(log_mod, "_interruptible_sleep", return_value=None),
        ):
            before_a = time.monotonic()
            _fetch_log_unit(
                "dep1",
                None,
                None,
                None,
                "",
                S,
                E,
                cancelled=cancelled,
                rate_limit_signal=rate_limit_signal,
            )
        # base_delay=1.0 * 2**0 * uniform(...)=1.0 -> cooldown=1.0s.
        deadline_a = rate_limit_signal._until
        self.assertAlmostEqual(deadline_a - before_a, 1.0, delta=0.4)

        fake_b = _RecordingFakeLogAPI({
            (S, E): [
                LogAPIError("rate limited", 429, retry_after=None),
                _loki_response([(S + 1, "b", {})]),
            ]
        })
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake_b)),
            patch.object(log_mod.random, "uniform", return_value=1.5),
            patch.object(log_mod, "_interruptible_sleep", return_value=None),
        ):
            before_b = time.monotonic()
            _fetch_log_unit(
                "dep1",
                None,
                None,
                None,
                "",
                S,
                E,
                cancelled=cancelled,
                rate_limit_signal=rate_limit_signal,
            )
        # base_delay=1.0 * 2**0 * uniform(...)=1.5 -> cooldown=1.5s, longer
        # than worker A's -- the shared deadline must extend to match it
        # (`_RateLimitSignal.signal` takes max(existing, new)).
        deadline_b = rate_limit_signal._until
        self.assertAlmostEqual(deadline_b - before_b, 1.5, delta=0.4)
        self.assertGreater(deadline_b, deadline_a)
        # Not a fixed 2.0s default cooldown regardless of either worker's
        # own jittered delay.
        self.assertLess(deadline_a - before_a, 2.0)
        self.assertNotAlmostEqual(deadline_a - before_a, 2.0, delta=0.1)


class TestFetchLogUnit429Backoff(unittest.TestCase):
    """429 retry/backoff math."""

    def test_retry_after_honored_and_bounded_to_60s_cap(self):
        """Table-driven: a `Retry-After` under the 60s cap is honored
        verbatim; one above the cap is bounded to exactly 60s."""
        cases = [
            ("under cap", 3.0, 3.0),
            ("above cap", 600.0, 60.0),
        ]
        for description, retry_after, expected_sleep in cases:
            with self.subTest(description=description):
                fake = _RecordingFakeLogAPI({
                    (0, 100): [
                        LogAPIError("rate limited", 429, retry_after=retry_after),
                        _loki_response([(1, "a", {})]),
                    ]
                })
                sleeps = []
                with (
                    patch.object(log_mod, "APIClient", _make_client_class(fake)),
                    patch.object(
                        log_mod.time, "sleep", side_effect=lambda d: sleeps.append(d)
                    ),
                ):
                    result = _fetch_log_unit(
                        None, "job-1", None, None, "", 0, 100, limit=5000
                    )
                self.assertFalse(result.failed)
                self.assertEqual(sleeps, [expected_sleep])

    def test_non_429_status_uses_fixed_backoff_not_retry_after_or_jitter(self):
        fake = _RecordingFakeLogAPI({
            (0, 100): [
                LogAPIError("server error", 500),
                _loki_response([(1, "a", {})]),
            ]
        })
        sleeps = []
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.time, "sleep", side_effect=lambda d: sleeps.append(d)),
        ):
            _fetch_log_unit(None, "job-1", None, None, "", 0, 100, limit=5000)
        self.assertEqual(sleeps, [1.0])

    def test_non_429_backoff_follows_exact_exponential_schedule(self):
        """Table-driven: the full non-429 backoff schedule across
        `_ADAPTIVE_RETRY_MAX_ATTEMPTS - 1` consecutive failures is exactly
        `base_delay * 2**attempt` for attempt in
        0..`_ADAPTIVE_RETRY_MAX_ATTEMPTS - 2` (1/2/4/8s with the current
        constants) -- the 5th (final) attempt succeeds, so no 5th sleep is
        recorded. Expected values are derived from the named module
        constants, not hardcoded literals, so this test cannot silently
        drift from production if the constants ever change.
        """
        self.assertEqual(_ADAPTIVE_RETRY_MAX_ATTEMPTS, 5)
        num_failures = _ADAPTIVE_RETRY_MAX_ATTEMPTS - 1
        expected = [
            _ADAPTIVE_RETRY_BASE_DELAY_SEC * (2**attempt)
            for attempt in range(num_failures)
        ]
        script = [LogAPIError("server error", 500) for _ in range(num_failures)]
        script.append(_loki_response([(1, "a", {})]))
        fake = _RecordingFakeLogAPI({(0, 100): script})
        sleeps = []
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.time, "sleep", side_effect=lambda d: sleeps.append(d)),
        ):
            result = _fetch_log_unit(None, "job-1", None, None, "", 0, 100, limit=5000)
        self.assertFalse(result.failed)
        self.assertEqual(len(fake.calls), _ADAPTIVE_RETRY_MAX_ATTEMPTS)
        self.assertEqual(sleeps, expected)

    def test_jittered_backoff_stays_within_bounds_and_varies_across_calls(self):
        # No Retry-After header: delay = min(60, 1.0 * 2**0 * uniform(1.0, 1.5))
        # on attempt 0, so every observed delay must fall in [1.0, 1.5), and
        # repeated calls must not all produce the identical delay (jitter).
        delays = []
        for _ in range(20):
            fake = _RecordingFakeLogAPI({
                (0, 100): [
                    LogAPIError("rate limited", 429, retry_after=None),
                    _loki_response([(1, "a", {})]),
                ]
            })
            captured = []
            with (
                patch.object(log_mod, "APIClient", _make_client_class(fake)),
                patch.object(
                    log_mod.time, "sleep", side_effect=lambda d: captured.append(d)
                ),
            ):
                _fetch_log_unit(None, "job-1", None, None, "", 0, 100, limit=5000)
            delays.append(captured[0])
        for d in delays:
            self.assertGreaterEqual(d, 1.0)
            self.assertLess(d, 1.5)
        self.assertGreater(len(set(delays)), 1)

    def test_cancelled_is_checked_before_a_429_sleep(self):
        # A 429 sleep must not run to completion once `cancelled` becomes
        # set, even mid-retry-loop.
        cancelled = threading.Event()

        class _FakeSetsCancelledThen429:
            def __init__(self):
                self.calls = 0

            def get_log(self, **kwargs):
                self.calls += 1
                cancelled.set()
                raise LogAPIError("rate limited", 429, retry_after=5.0)

        fake = _FakeSetsCancelledThen429()
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.time, "sleep") as mock_sleep,
        ):
            result = _fetch_log_unit(
                None, "job-1", None, None, "", 0, 100, limit=5000, cancelled=cancelled
            )
        self.assertTrue(result.failed)
        mock_sleep.assert_not_called()
        self.assertEqual(fake.calls, 1)

    def test_429_signals_the_shared_rate_limit_signal(self):
        fake = _RecordingFakeLogAPI({
            (0, 100): [
                LogAPIError("rate limited", 429, retry_after=None),
                _loki_response([(1, "a", {})]),
            ]
        })
        signal = _RateLimitSignal()
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.time, "sleep", return_value=None),
        ):
            _fetch_log_unit(
                None,
                "job-1",
                None,
                None,
                "",
                0,
                100,
                limit=5000,
                rate_limit_signal=signal,
            )
        self.assertTrue(signal.active())

    def test_exhausted_429_retries_resolve_as_failed_unit_without_raising(self):
        """Repeated 429s never abort the run, only fail the unit."""
        fake = _RecordingFakeLogAPI({(0, 100): LogAPIError("rate limited", 429)})
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.time, "sleep", return_value=None),
        ):
            result = _fetch_log_unit(None, "job-1", None, None, "", 0, 100, limit=5000)
        self.assertTrue(result.failed)
        self.assertEqual(len(fake.calls), 5)

    def test_negative_or_zero_retry_after_header_falls_back_to_jittered_backoff(self):
        """Table-driven guard against a negative/zero `Retry-After` header: a
        naive `_parse_retry_after` could return the negative/zero float
        unchanged, which would flow into `_fetch_log_unit`'s
        `delay = min(e.retry_after, retry_after_cap)` (still negative/zero)
        and then `_interruptible_sleep(delay, cancelled)` ->
        `cancelled.wait(-5.0)` (or `wait(0)`, masking the bug for the zero
        case), raising an uncaught `ValueError` inside the worker thread for
        the negative case. Drives a real `LogAPI` against a fake HTTP
        transport (not a synthetic, already-constructed `LogAPIError`), so
        this exercises the actual `_parse_retry_after` parsing path
        end-to-end for both header values.
        """
        # start=0 is rejected by the real LogAPI's own epoch-zero
        # precondition (a different regression, covered elsewhere) -- use a
        # non-zero start so that check doesn't shadow this one.
        S, E = 1000, 1100
        for description, header_value in (
            ("negative Retry-After", "-5"),
            ("zero Retry-After", "0"),
        ):
            with self.subTest(description=description):
                http_client = _RealLogAPIHTTPClient()
                retry_after_response = _FakeHTTPResponse(
                    None, ok=False, status_code=429, text="rate limited"
                )
                retry_after_response.headers["Retry-After"] = header_value
                http_client._get.side_effect = [
                    retry_after_response,
                    _FakeHTTPResponse({"data": {"result": []}}),
                ]
                real_log_api = LogAPI(http_client)
                cancelled = threading.Event()

                # No `_interruptible_sleep`/`time.sleep` mocking here --
                # a regression would raise an uncaught `ValueError` from
                # `cancelled.wait(-5.0)` before ever returning. Real (short,
                # jittered ~1.0-1.5s) backoff sleep is allowed to happen.
                with patch.object(
                    log_mod, "APIClient", _make_client_class(real_log_api)
                ):
                    result = _fetch_log_unit(
                        "dep1", None, None, None, "", S, E, cancelled=cancelled
                    )

                self.assertFalse(result.failed)
                self.assertEqual(http_client._get.call_count, 2)


class TestParseLogEntriesMalformedShapes(unittest.TestCase):
    """Malformed response shapes raise, never silently
    default to an empty page.
    """

    def test_malformed_top_level_response_shapes_raise(self):
        """Table-driven: each case violates the response wrapper's own
        top-level structure (as opposed to a single record's shape, tabled
        separately below) and must raise `_MalformedLogResponseError`."""
        malformed_responses = [
            ("missing 'data' key", {"error": "something went wrong"}),
            ("'data' not a dict", {"data": "not-a-dict"}),
            ("'result' not a list", {"data": {"result": "not-a-list"}}),
            (
                "result entry missing 'values' key",
                {"data": {"result": [{"stream": {"pod": "p1"}}]}},
            ),
            (
                "malformed values tuple",
                {"data": {"result": [{"stream": {}, "values": [["only-one"]]}]}},
            ),
            ("response not a dict", ["not", "a", "dict"]),
        ]
        for description, response in malformed_responses:
            with self.subTest(description=description):
                with self.assertRaises(_MalformedLogResponseError):
                    _parse_log_entries(response, limit=100, start=0, end=1_000_000)

    def test_legitimately_empty_page_does_not_raise(self):
        """A well-formed empty result is not malformed."""
        entries, examined = _parse_log_entries(
            {"data": {"result": []}}, limit=100, start=0, end=1_000_000
        )
        self.assertEqual(entries, [])
        self.assertEqual(examined, 0)

    def test_out_of_range_entry_raises(self):
        """The `[start, end)` range check now runs inside `_parse_log_entries`
        itself, over every examined record."""
        with self.assertRaises(_MalformedLogResponseError):
            _parse_log_entries(
                _loki_response([(2500, "bad", {})]), limit=100, start=1000, end=2000
            )

    def test_end_exclusive_boundary_entry_raises(self):
        with self.assertRaises(_MalformedLogResponseError):
            _parse_log_entries(
                _loki_response([(2000, "edge", {})]), limit=100, start=1000, end=2000
            )

    def test_within_range_entry_is_retained(self):
        entries, examined = _parse_log_entries(
            _loki_response([(1500, "ok", {})]), limit=100, start=1000, end=2000
        )
        self.assertEqual(examined, 1)
        self.assertEqual([e.timestamp_ns for e in entries], [1500])

    def test_malformed_stream_or_value_element_shapes_raise(self):
        """Table-driven: each case varies either the `stream` dict or a
        `values` element (not the top-level response-wrapper shapes tabled
        above, nor the value-tuple length/metadata-type/timestamp-type
        forms tabled separately in
        `test_malformed_value_tuple_shapes_and_metadata_forms_are_rejected`
        below) and must raise `_MalformedLogResponseError`."""
        malformed_records = [
            (
                # A stream label value that isn't a hashable scalar would
                # make the resulting `LogEntry` unhashable, only failing
                # later at the scheduler's flush-time dedup -- reject it
                # here instead.
                "unhashable stream label value",
                {"stream": {"pod": ["not", "hashable"]}, "values": [["1500", "line"]]},
            ),
            (
                "unhashable metadata value",
                {
                    "stream": {"pod": "p1"},
                    "values": [["1500", "line", {"k": {"nested": 1}}]],
                },
            ),
            (
                "non-dict metadata element",
                {
                    "stream": {"pod": "p1"},
                    "values": [["1500", "line", ["not", "a", "dict"]]],
                },
            ),
            (
                "non-string line value",
                {"stream": {"pod": "p1"}, "values": [["1500", 12345]]},
            ),
            (
                # A stream dict with a non-`str` key (mixed `str`/`int`
                # keys) would make `sorted(stream.items())` raise a raw,
                # undiagnosable `TypeError` instead of
                # `_MalformedLogResponseError` -- `assertRaises`' exact-type
                # check fails the subTest if a bare `TypeError` propagates.
                "non-str stream key raises malformed, not a bare TypeError",
                {"stream": {"pod": "p1", 7: "bad"}, "values": [["1500", "line"]]},
            ),
            (
                "non-str metadata key raises malformed, not a bare TypeError",
                {
                    "stream": {"pod": "p1"},
                    "values": [["1500", "line", {"a": 1, 2: "bad"}]],
                },
            ),
        ]
        for description, record in malformed_records:
            with self.subTest(description=description):
                with self.assertRaises(_MalformedLogResponseError):
                    _parse_log_entries(
                        {"data": {"result": [record]}},
                        limit=100,
                        start=1000,
                        end=2000,
                    )

    def test_legitimate_scalar_metadata_is_unaffected(self):
        """Control: str/int/float/bool/None metadata values are all
        supported hashable scalars and must not be rejected."""
        entries, examined = _parse_log_entries(
            {
                "data": {
                    "result": [{
                        "stream": {"pod": "p1"},
                        "values": [[
                            "1500",
                            "line",
                            {
                                "str_field": "v",
                                "int_field": 1,
                                "float_field": 1.5,
                                "bool_field": True,
                                "none_field": None,
                            },
                        ]],
                    }]
                }
            },
            limit=100,
            start=1000,
            end=2000,
        )
        self.assertEqual(examined, 1)
        self.assertEqual(
            dict(entries[0].metadata),
            {
                "str_field": "v",
                "int_field": 1,
                "float_field": 1.5,
                "bool_field": True,
                "none_field": None,
            },
        )

    def test_malformed_value_tuple_shapes_and_metadata_forms_are_rejected(self):
        """Table-driven: value-tuple length bound and metadata
        acceptance/rejection (`None`/`{}` accepted as "no metadata", any
        other non-dict rejected even when falsy), plus timestamp type
        rejection (`bool`/`float`). `start` (1000) is a valid/retained
        boundary; the exclusive `end` (2000) boundary is already covered
        by `test_end_exclusive_boundary_entry_raises` above and is not
        repeated here."""
        start, end = 1000, 2000
        valid_cases = [
            ("2-element, no metadata", [1500, "line"], ()),
            ("3-element, None metadata", [1500, "line", None], ()),
            ("3-element, {} metadata", [1500, "line", {}], ()),
            (
                "3-element, real metadata dict",
                [1500, "line", {"k": "v"}],
                (("k", "v"),),
            ),
            ("str timestamp that parses cleanly", ["1500", "line"], ()),
            ("timestamp exactly at start boundary", [start, "line"], ()),
        ]
        for description, value, expected_metadata in valid_cases:
            with self.subTest(description=description):
                entries, examined = _parse_log_entries(
                    {
                        "data": {
                            "result": [{"stream": {"pod": "p1"}, "values": [value]}]
                        }
                    },
                    limit=100,
                    start=start,
                    end=end,
                )
                self.assertEqual(examined, 1)
                self.assertEqual(entries[0].timestamp_ns, int(value[0]))
                self.assertEqual(entries[0].line, "line")
                self.assertEqual(entries[0].metadata, expected_metadata)

        malformed_cases = [
            ("0-element value tuple", []),
            ("1-element value tuple", [1500]),
            ("4-element value tuple", [1500, "line", {}, "extra"]),
            ("5-element value tuple", [1500, "line", {}, "extra", "extra2"]),
            ("metadata 0 (falsy, wrong type)", [1500, "line", 0]),
            ("metadata False (falsy, wrong type)", [1500, "line", False]),
            ("metadata empty string (falsy, wrong type)", [1500, "line", ""]),
            ("metadata empty list (falsy, wrong type)", [1500, "line", []]),
            ("metadata non-dict truthy string", [1500, "line", "x"]),
            ("positive float timestamp", [1500.5, "line"]),
        ]
        for description, value in malformed_cases:
            with self.subTest(description=description):
                with self.assertRaises(_MalformedLogResponseError):
                    _parse_log_entries(
                        {
                            "data": {
                                "result": [{
                                    "stream": {"pod": "p1"},
                                    "values": [value],
                                }]
                            }
                        },
                        limit=100,
                        start=start,
                        end=end,
                    )

        # Bracket -10..10 so these values (coerced via int(): True->1,
        # False->0, -1.0->-1) fall in-range -- otherwise the pre-existing
        # range check would reject them too, masking the type check below.
        in_range_start, in_range_end = -10, 10
        type_rejected_in_range_cases = [
            ("bool timestamp True", [True, "line"]),
            ("bool timestamp False", [False, "line"]),
            ("negative float timestamp", [-1.0, "line"]),
        ]
        for description, value in type_rejected_in_range_cases:
            with self.subTest(description=description):
                with self.assertRaises(_MalformedLogResponseError):
                    _parse_log_entries(
                        {
                            "data": {
                                "result": [{
                                    "stream": {"pod": "p1"},
                                    "values": [value],
                                }]
                            }
                        },
                        limit=100,
                        start=in_range_start,
                        end=in_range_end,
                    )

    def test_limit_must_be_a_positive_int_raises_value_error(self):
        """`limit` is an internal contract between this parser and its
        callers (always `_ADAPTIVE_PAGE_LIMIT` in production), not data
        from the backend -- a bad value here is our own bug, so it raises
        plain `ValueError`, distinct from `_MalformedLogResponseError`
        (reserved for untrusted response-shape violations). Unreachable
        from real CLI usage; defensive only."""
        valid_response = _loki_response([(1500, "ok", {})])
        for bad_limit in (0, -1, True, "5", 1.5):
            with self.subTest(bad_limit=bad_limit):
                with self.assertRaises(ValueError):
                    _parse_log_entries(
                        valid_response, limit=bad_limit, start=1000, end=2000
                    )


class TestStreamValidationRunsOncePerStreamNotPerRecord(unittest.TestCase):
    """`_validate_hashable_scalar_values`/`_validate_str_keys` on `stream`
    must run once per stream dict, not once per record within that stream --
    otherwise validation cost scales with record count instead of stream
    count."""

    def test_call_count_scales_with_stream_count_not_record_count(self):
        entries = [(1000 + i, f"l{i}", {"pod": "p1"}) for i in range(500)]
        response = _loki_response(entries)
        self.assertEqual(len(response["data"]["result"]), 1)  # single stream

        with (
            patch.object(
                log_mod,
                "_validate_hashable_scalar_values",
                wraps=log_mod._validate_hashable_scalar_values,
            ) as scalar_mock,
            patch.object(
                log_mod, "_validate_str_keys", wraps=log_mod._validate_str_keys
            ) as keys_mock,
        ):
            entries_out, examined = _parse_log_entries(
                response, limit=1000, start=1000, end=2000
            )

        self.assertEqual(examined, 500)
        # One stream dict validated once each, not once per the 500 records.
        stream_scalar_calls = [
            c for c in scalar_mock.call_args_list if c.args[1] == "stream"
        ]
        stream_key_calls = [
            c for c in keys_mock.call_args_list if c.args[1] == "stream"
        ]
        self.assertEqual(len(stream_scalar_calls), 1)
        self.assertEqual(len(stream_key_calls), 1)

    def test_invalid_stream_with_empty_values_still_raises(self):
        """Validating `stream` before the per-record loop means a stream
        with an invalid value is rejected even when `values` is empty --
        the loop body never running must not let a bad `stream` dict slip
        through."""
        with self.assertRaises(_MalformedLogResponseError):
            _parse_log_entries(
                {
                    "data": {
                        "result": [{
                            "stream": {"pod": ["not", "hashable"]},
                            "values": [],
                        }]
                    }
                },
                limit=100,
                start=1000,
                end=2000,
            )

    def test_invalid_stream_key_with_empty_values_still_raises(self):
        with self.assertRaises(_MalformedLogResponseError):
            _parse_log_entries(
                {
                    "data": {
                        "result": [{
                            "stream": {"pod": "p1", 7: "bad"},
                            "values": [],
                        }]
                    }
                },
                limit=100,
                start=1000,
                end=2000,
            )


class TestFetchLogUnitMalformedAndOutOfRange(unittest.TestCase):
    def test_malformed_or_out_of_range_response_is_retried_then_resolves_failed(self):
        """Table-driven: every kind of malformed/out-of-range response drives
        the same `_fetch_log_unit` retry-then-fail path -- a wrong-shape
        response, an out-of-range timestamp (treated as malformed, not
        silently dropped), a timestamp exactly at the exclusive `end`
        boundary (half-open `[start, end)`), a too-short value tuple, a
        non-dict/falsy metadata value, and a `bool` timestamp.

        The "bool timestamp" case uses its own `start`/`end` bracketing
        `int(True) == 1` (rather than the shared `[1000, 2000)` used by the
        other cases): `[1000, 2000)` would reject `True` via the
        pre-existing `[start, end)` range check regardless of whether the
        dedicated `isinstance(value[0], (bool, float))` type check exists,
        masking which check actually drove the failure.
        """
        cases = {
            "wrong shape": (0, 100, {"error": "wrong shape"}),
            "out-of-range timestamp": (
                1000,
                2000,
                _loki_response([(2500, "bad", {})]),
            ),
            "timestamp at exclusive end boundary": (
                1000,
                2000,
                _loki_response([(2000, "edge", {})]),
            ),
            "bad value-tuple length": (
                1000,
                2000,
                {"data": {"result": [{"stream": {}, "values": [["1500"]]}]}},
            ),
            "bad metadata (non-dict, falsy)": (
                1000,
                2000,
                {"data": {"result": [{"stream": {}, "values": [["1500", "line", 0]]}]}},
            ),
            "bool timestamp": (
                -10,
                10,
                {"data": {"result": [{"stream": {}, "values": [[True, "line"]]}]}},
            ),
        }
        for description, (start, end, response) in cases.items():
            with self.subTest(description=description):
                fake = _RecordingFakeLogAPI({(start, end): response})
                with (
                    patch.object(log_mod, "APIClient", _make_client_class(fake)),
                    patch.object(log_mod.time, "sleep", return_value=None),
                ):
                    result = _fetch_log_unit(
                        None, "job-1", None, None, "", start, end, limit=5000
                    )
                self.assertTrue(result.failed)
                self.assertEqual(len(fake.calls), 5)

    def test_fetch_log_unit_bad_limit_raises_immediately_with_no_api_calls(self):
        """Fix (`limit` precondition) at the `_fetch_log_unit` layer:
        `limit` is validated at the top of `_fetch_log_unit`, before the
        retry loop and before any HTTP call, mirroring
        `_parse_log_entries`'s own precondition check. A bad `limit` is a
        programmer/configuration bug, never legitimately caused by
        backend data, so it must raise a plain `ValueError` immediately --
        zero API calls, zero retries -- rather than being caught by the
        loop's bare `except Exception` and wastefully retried the full
        budget before resolving `failed=True`."""
        fake = _RecordingFakeLogAPI({(1000, 2000): _loki_response([(1500, "ok", {})])})
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.time, "sleep", return_value=None),
        ):
            with self.assertRaises(ValueError):
                _fetch_log_unit(None, "job-1", None, None, "", 1000, 2000, limit=0)
        self.assertEqual(len(fake.calls), 0)


class TestFetchLogUnitOversizedPageCapping(unittest.TestCase):
    def test_response_at_or_over_limit_is_capped_and_saturated(self):
        """Table-driven: a response strictly over `limit` is capped to the
        `limit` smallest timestamps; a response of exactly `limit` entries
        is also saturated (not just capped on strict overflow)."""
        cases = [
            ("over limit", 7000, 4999, [0, 1, 2]),
            ("exactly at limit", 5000, None, None),
        ]
        for description, entry_count, expected_max_ts, expected_head in cases:
            with self.subTest(description=description):
                entries = [(i, f"l{i}", {}) for i in range(entry_count)]
                fake = _RecordingFakeLogAPI({(0, 100000): _loki_response(entries)})
                with patch.object(log_mod, "APIClient", _make_client_class(fake)):
                    result = _fetch_log_unit(
                        None, "job-1", None, None, "", 0, 100000, limit=5000
                    )
                self.assertTrue(result.saturated)
                self.assertEqual(len(result.entries), 5000)
                if expected_max_ts is not None:
                    self.assertEqual(result.max_ts, expected_max_ts)
                    self.assertEqual(
                        [e.timestamp_ns for e in result.entries][:3], expected_head
                    )


class TestBoundedIncrementalPageCapping(unittest.TestCase):
    """`_parse_log_entries` bounds retention to `limit` incrementally
    (a bounded max-heap) as the response is examined, instead of
    materializing and sorting the full response before capping it.
    """

    def test_unordered_interleaved_across_streams_retains_exact_smallest_limit(
        self,
    ):
        # 450 entries (4.5x the 100 limit) spread across 5 streams, with
        # timestamps assigned via a multiplicative permutation modulo 450
        # (97 is coprime with 450, so `(i * 97) % 450` visits every
        # timestamp exactly once, in an order matching neither within- nor
        # across-stream examination order) -- so neither a single stream's
        # `values` list nor `data.result`'s stream order is ever sorted.
        limit = 100
        total = 450
        entries = []
        for i in range(total):
            ts = (i * 97) % total
            entries.append((ts, f"l{ts}", {"pod": f"p{i % 5}"}))
        fake = _RecordingFakeLogAPI({(0, total): _loki_response(entries)})
        with patch.object(log_mod, "APIClient", _make_client_class(fake)):
            result = _fetch_log_unit(
                None, "job-1", None, None, "", 0, total, limit=limit
            )
        self.assertTrue(result.saturated)
        self.assertEqual(len(result.entries), limit)
        # The true smallest-`limit` timestamps are exactly 0..limit-1,
        # sorted ascending, regardless of examination order.
        self.assertEqual([e.timestamp_ns for e in result.entries], list(range(limit)))

    def test_malformed_record_in_unretained_portion_still_raises(self):
        # limit=5 over ts 0..19 retains only 0..4; the malformed record is
        # appended after all 20 well-formed values, so it is examined well
        # after the retained set is already full -- it must still raise,
        # never be silently dropped just because it wouldn't have been kept.
        limit = 5
        entries = [(i, f"l{i}", {}) for i in range(20)]
        response = _loki_response(entries)
        response["data"]["result"][0]["values"].append(["not-enough-fields"])
        fake = _RecordingFakeLogAPI({(0, 100): response})
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.time, "sleep", return_value=None),
        ):
            result = _fetch_log_unit(None, "job-1", None, None, "", 0, 100, limit=limit)
        self.assertTrue(result.failed)

    def test_out_of_range_record_in_unretained_portion_still_raises(self):
        # Same shape as above, but the bad record is out-of-range rather
        # than malformed-shaped -- also examined after the retained set is
        # already full.
        limit = 5
        entries = [(i, f"l{i}", {}) for i in range(20)]
        entries.append((99999, "way-out-of-range", {}))
        fake = _RecordingFakeLogAPI({(0, 100): _loki_response(entries)})
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.time, "sleep", return_value=None),
        ):
            result = _fetch_log_unit(None, "job-1", None, None, "", 0, 100, limit=limit)
        self.assertTrue(result.failed)

    def test_normal_under_limit_response_unchanged_behavior(self):
        # Control case: a normal, well-under-the-limit, unordered response
        # is unaffected by the incremental bounded-retention rewrite.
        entries = [(3, "c", {}), (1, "a", {}), (2, "b", {})]
        fake = _RecordingFakeLogAPI({(0, 100): _loki_response(entries)})
        with patch.object(log_mod, "APIClient", _make_client_class(fake)):
            result = _fetch_log_unit(None, "job-1", None, None, "", 0, 100, limit=5000)
        self.assertFalse(result.saturated)
        self.assertFalse(result.failed)
        self.assertEqual([e.timestamp_ns for e in result.entries], [1, 2, 3])
        self.assertEqual(result.min_ts, 1)
        self.assertEqual(result.max_ts, 3)

    def test_bounded_heap_size_never_exceeds_limit_for_large_response(self):
        # Black-box instrumentation of the bounded max-heap's own insert
        # operations (heapq.heappush/heapreplace), not a read of the source
        # file or an AST inspection: confirms additional retained-object
        # count stays proportional to `limit`, not to response size, even
        # for a response many times larger than `limit`.
        limit = 10
        total = 5000
        entries = [((i * 97) % total, f"l{i}", {}) for i in range(total)]
        fake = _RecordingFakeLogAPI({(0, total): _loki_response(entries)})

        real_heappush = heapq.heappush
        real_heapreplace = heapq.heapreplace
        max_heap_len = {"value": 0}

        def tracking_heappush(heap, item):
            real_heappush(heap, item)
            max_heap_len["value"] = max(max_heap_len["value"], len(heap))

        def tracking_heapreplace(heap, item):
            real_heapreplace(heap, item)
            max_heap_len["value"] = max(max_heap_len["value"], len(heap))

        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.heapq, "heappush", side_effect=tracking_heappush),
            patch.object(
                log_mod.heapq, "heapreplace", side_effect=tracking_heapreplace
            ),
        ):
            result = _fetch_log_unit(
                None, "job-1", None, None, "", 0, total, limit=limit
            )
        self.assertTrue(result.saturated)
        self.assertGreater(max_heap_len["value"], 0)
        self.assertLessEqual(max_heap_len["value"], limit)


class TestFetchLogUnitRejectsEpochZeroBoundary(unittest.TestCase):
    """A literal `start=0`/`end=0` unit boundary can never actually reach
    `_fetch_log_unit` in production -- `fetch_log`'s probe call rejects an
    epoch-0 `--start`/`--end` before the adaptive scheduler ever starts (see
    test_log_cli.py's `TestEpochZeroStartEndToEndCli`), and bisection never
    produces a unit boundary below the original start. This exercises the
    defense-in-depth case anyway: if `_fetch_log_unit` were ever given such a
    boundary, `LogAPI.get_log` rejects it with a plain `RuntimeError`, which
    `_fetch_log_unit`'s existing non-429 retry path treats like any other
    failure -- retried with fixed backoff, then reported as a failed unit
    once retries are exhausted, not an unhandled crash.
    """

    def test_zero_boundary_exhausts_retries_and_is_reported_failed(self):
        fake = _RecordingFakeLogAPI({
            (0, 100): RuntimeError(
                "start=0/end=0 cannot be distinguished from an omitted"
                " start/end by the /logs API"
            )
        })
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod, "_interruptible_sleep", return_value=None),
        ):
            result = _fetch_log_unit(None, "job-1", None, None, "", 0, 100, limit=5000)
        self.assertTrue(result.failed)
        self.assertEqual(len(fake.calls), 5)


class TestInterruptibleBackoffSleep(unittest.TestCase):
    """Backoff/retry sleeps use `cancelled.wait(delay)`,
    which wakes promptly once `cancelled` is set instead of always blocking
    for the full configured delay. Verified with real wall-clock timing.
    """

    def test_cancellation_during_non_429_backoff_wakes_promptly(self):
        # attempt=0 non-429 failure -> fixed backoff delay = 1.0s. A
        # background timer sets `cancelled` well before that elapses.
        fake = _RecordingFakeLogAPI({(0, 100): RuntimeError("boom")})
        cancelled = threading.Event()
        timer = threading.Timer(0.05, cancelled.set)
        timer.start()
        try:
            start = time.perf_counter()
            with patch.object(log_mod, "APIClient", _make_client_class(fake)):
                result = _fetch_log_unit(
                    None,
                    "job-1",
                    None,
                    None,
                    "",
                    0,
                    100,
                    limit=5000,
                    cancelled=cancelled,
                )
            elapsed = time.perf_counter() - start
        finally:
            timer.cancel()
        self.assertTrue(result.failed)
        # Woke well before the full 1.0s fixed-backoff delay would have
        # elapsed on its own.
        self.assertLess(elapsed, 0.3)

    def test_cancellation_during_retry_after_bounded_sleep_wakes_promptly(self):
        # A 429 with retry_after=10.0 would otherwise sleep a full 10s.
        fake = _RecordingFakeLogAPI(
            {(0, 100): LogAPIError("rate limited", 429, retry_after=10.0)}
        )
        cancelled = threading.Event()
        timer = threading.Timer(0.05, cancelled.set)
        timer.start()
        try:
            start = time.perf_counter()
            with patch.object(log_mod, "APIClient", _make_client_class(fake)):
                result = _fetch_log_unit(
                    None,
                    "job-1",
                    None,
                    None,
                    "",
                    0,
                    100,
                    limit=5000,
                    cancelled=cancelled,
                )
            elapsed = time.perf_counter() - start
        finally:
            timer.cancel()
        self.assertTrue(result.failed)
        # Woke well before the full (capped) 10s Retry-After delay.
        self.assertLess(elapsed, 2.0)

    def test_no_cancelled_event_falls_back_to_time_sleep(self):
        # cancelled=None falls back to plain time.sleep.
        fake = _RecordingFakeLogAPI(
            {
                (0, 100): [
                    RuntimeError("e1"),
                    _loki_response([(1, "ok", {})]),
                ]
            }
        )
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.time, "sleep", return_value=None) as mock_sleep,
        ):
            result = _fetch_log_unit(
                None, "job-1", None, None, "", 0, 100, limit=5000, cancelled=None
            )
        self.assertFalse(result.failed)
        mock_sleep.assert_called_once_with(1.0)

    def test_control_backoff_sleep_not_shortened_without_cancellation(self):
        """Control: proves the interruptible-wait mechanism doesn't shorten the delay when
        cancellation never happens -- the full ~1.0s fixed backoff still
        elapses before attempt 2 fires."""
        fake = _RecordingFakeLogAPI(
            {(0, 100): [RuntimeError("boom"), _loki_response([(1, "ok", {})])]}
        )
        cancelled = threading.Event()

        with patch.object(log_mod, "APIClient", _make_client_class(fake)):
            start = time.perf_counter()
            result = _fetch_log_unit(
                None, "job-1", None, None, "", 0, 100, limit=5000, cancelled=cancelled
            )
            elapsed = time.perf_counter() - start

        self.assertFalse(result.failed)
        self.assertGreaterEqual(
            elapsed,
            0.95,
            "expected the full ~1.0s fixed backoff to elapse when"
            f" cancellation never happens, got {elapsed}s",
        )
        self.assertEqual(len(fake.calls), 2)
