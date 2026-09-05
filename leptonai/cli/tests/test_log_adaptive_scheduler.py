"""Unit tests for state owned by `_AdaptiveLogScheduler` itself: bisection
math (including the fetched-interval midpoint heuristic for one- vs
two-child splits), watermark computation, split/same-timestamp decisions,
admission arithmetic, and the real-thread integrations that require genuine
concurrency (chronological output despite reverse completion order, the
frontier-exemption deadlock regression, and sink-failure cancellation of an
already-in-flight request).

Single-request-cycle behavior (`_parse_log_entries`, `LogEntry` identity,
`_fetch_log_unit` retry/backoff) lives in `test_log_adaptive_worker.py`.
Output/sink formatting lives in `test_log_adaptive_output.py`. Tests call
`_fetch_log_unit` and `fetch_logs_adaptive_parallel` directly (both are
public module-level symbols) rather than going through the full
`lep log get` CLI invocation.
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

from loguru import logger

from leptonai.api.v2.log import LogAPIError
from leptonai.cli import log as log_mod
from leptonai.cli.log import (
    FetchUnitResult,
    LogEntry,
    WorkUnit,
    _AdaptiveLogScheduler,
    _fetch_log_unit,
    fetch_logs_adaptive_parallel,
)
from leptonai.cli.tests._log_test_helpers import (
    RecordingFakeLogAPI as _RecordingFakeLogAPI,
    loki_response as _loki_response,
    make_client_class as _make_client_class,
    pad_entries as _pad_entries,
    two_unit_cancellation_fixture as _two_unit_cancellation_fixture,
    wait_for_quiescent_threads as _wait_for_quiescent_threads,
)


class TestAdaptiveSchedulerBisection(unittest.TestCase):
    """The fetched-interval-midpoint split heuristic:
    saturation at/past the midpoint of the *fetched* unit yields one child
    covering the whole remainder; saturation before it yields two children
    bisecting the remainder.
    """

    def test_saturation_relative_to_fetched_midpoint_controls_child_count(self):
        """Table-driven: unit=[0, 20000), fetched_mid=10000. A saturated
        first page with max_ts >= fetched_mid yields exactly one child
        covering the remainder; max_ts < fetched_mid bisects the remainder
        into two children instead."""
        mid = 9999 + (20000 - 9999) // 2
        cases = [
            (
                "at/past fetched midpoint -> single child",
                [(t, f"l{t}", {}) for t in range(5000, 15000)],
                {(14999, 20000): _loki_response([(15500, "tail", {})])},
                {(0, 20000), (14999, 20000)},
            ),
            (
                "before fetched midpoint -> two children",
                [(t, f"l{t}", {}) for t in range(0, 10000)],
                {
                    (9999, mid): _loki_response([(10100, "a", {})]),
                    (mid, 20000): _loki_response([(18000, "b", {})]),
                },
                {(0, 20000), (9999, mid), (mid, 20000)},
            ),
        ]
        for description, first_page, children_script, expected_ranges in cases:
            with self.subTest(description=description):
                self.assertEqual(len(first_page), 10000)
                fake = _RecordingFakeLogAPI({
                    (0, 20000): _loki_response(first_page),
                    **children_script,
                })
                with (
                    patch.object(log_mod, "APIClient", _make_client_class(fake)),
                    self.assertRaises(SystemExit) as cm,
                    patch.object(log_mod.console, "print"),
                ):
                    fetch_logs_adaptive_parallel(
                        None, "job-1", None, None, "", 0, 20000, 4, True, None
                    )
                self.assertEqual(cm.exception.code, 0)
                requested_ranges = {(c["start"], c["end"]) for c in fake.calls}
                self.assertEqual(requested_ranges, expected_ranges)
                self.assertEqual(len(fake.calls), len(expected_ranges))

    def test_all_calls_use_forward_direction(self):
        first_page = [(t, f"l{t}", {}) for t in range(5000, 15000)]
        fake = _RecordingFakeLogAPI({
            (0, 20000): _loki_response(first_page),
            (14999, 20000): _loki_response([(15500, "tail", {})]),
        })
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            self.assertRaises(SystemExit),
            patch.object(log_mod.console, "print"),
        ):
            fetch_logs_adaptive_parallel(
                None, "job-1", None, None, "", 0, 20000, 4, True, None
            )
        self.assertTrue(fake.calls)
        for call in fake.calls:
            self.assertEqual(call["direction"], "forward")


class TestChronologicalOutputAcrossRecursiveSplits(unittest.TestCase):
    """This never needs the CLI/Click layer, only
    `fetch_logs_adaptive_parallel` directly. Essential invariant #4
    (chronological watermark emission): a 3-leaf, 2-level
    bisecting tree where later-start (chronologically later) leaf units are
    made to resolve *first* via real, per-key delays under a real
    `ThreadPoolExecutor`, proving final output ordering reflects timestamp
    order, not completion order.

    Tree shape over [S, E): root saturates at T1=S+3000 (< branch_mid) ->
    two children C1=[S+3000, S+9500), C2=[S+9500, E). C1 saturates at
    T2=S+4000 (< its own branch_mid) -> two children D1=[S+4000, S+6750),
    D2=[S+6750, S+9500). C2 terminates without further splitting. Leaves:
    D1, D2, C2 -- three leaf units at different recursion depths.
    """

    S, E = 0, 16_000_000

    class _DelayedFakeLogAPI:
        def __init__(self, script, delay_fn):
            self.script = script
            self.delay_fn = delay_fn
            self.calls = []
            self.lock = threading.Lock()

        def get_log(self, **kwargs):
            key = (kwargs.get("start"), kwargs.get("end"))
            with self.lock:
                self.calls.append(dict(kwargs))
            time.sleep(self.delay_fn(key))
            outcome = self.script.get(key)
            if outcome is None:
                return {"data": {"result": []}}
            return outcome

    @classmethod
    def _delay_for(cls, key):
        start = key[0]
        frac = (start - cls.S) / (cls.E - cls.S)
        # Earlier-start units sleep longer, so later-start (chronologically
        # later) leaf units' futures resolve first.
        return max(0.002, 0.03 * (1 - frac))

    def _build_tree_script(self):
        S, E = self.S, self.E
        root_page = _pad_entries(10000, S + 0, S + 3_000_000, "r")
        c1_page = _pad_entries(10000, S + 3_000_000, S + 4_000_000, "c1")
        d1_resp = _loki_response(
            [(S + 4_500_000, "d1a", {}), (S + 4_600_000, "d1b", {})]
        )
        d2_resp = _loki_response([(S + 7_000_000, "d2a", {})])
        c2_resp = _loki_response([(S + 12_000_000, "c2a", {})])
        return {
            (S, E): _loki_response(root_page),
            (S + 3_000_000, S + 9_500_000): _loki_response(c1_page),
            (S + 4_000_000, S + 6_750_000): d1_resp,
            (S + 6_750_000, S + 9_500_000): d2_resp,
            (S + 9_500_000, E): c2_resp,
        }

    def test_chronological_output_regardless_of_completion_order(self):
        S, E = self.S, self.E
        script = self._build_tree_script()
        fake = self._DelayedFakeLogAPI(script, self._delay_for)
        outpath = os.path.join(tmpdir, "recursive_split_chronological_out.txt")

        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            self.assertRaises(SystemExit) as cm,
        ):
            fetch_logs_adaptive_parallel(
                None, "job-1", None, None, "", S, E, 4, True, outpath
            )

        self.assertEqual(cm.exception.code, 0)
        self.assertEqual(len(fake.calls), 5)

        with open(outpath, encoding="utf-8") as f:
            content = f.read()
        for marker in ("d1a", "d1b", "d2a", "c2a"):
            self.assertIn(marker, content)
        idx_d1a = content.index("d1a")
        idx_d1b = content.index("d1b")
        idx_d2a = content.index("d2a")
        idx_c2a = content.index("c2a")
        # d1 (ts=4500,4600) < d2 (ts=7000) < c2 (ts=12000), regardless of
        # which unit's future resolved first.
        self.assertTrue(idx_d1a < idx_d1b < idx_d2a < idx_c2a)


class TestAdaptiveSchedulerBoundaryDedup(unittest.TestCase):
    def test_boundary_timestamp_no_duplicate_no_drop(self):
        # unit=[0, 20000); fetched_mid=10000. Parent saturates with max_ts
        # (T)=14998 (>= fetched_mid) -> single child [14998, 20000). Parent's
        # page includes two boundary entries at ts=14998 that the child
        # re-fetches verbatim (exact duplicates), plus one entry the child
        # sees that the parent didn't.
        parent_entries = [(t, f"l{t}", {"pod": "p1"}) for t in range(5000, 14998)]
        parent_entries.append((14998, "boundary-A", {"pod": "p1"}))
        parent_entries.append((14998, "boundary-B", {"pod": "p1"}))
        self.assertEqual(len(parent_entries), 10000)

        child_entries = [
            (14998, "boundary-A", {"pod": "p1"}),  # exact duplicate of parent's
            (14998, "boundary-B", {"pod": "p1"}),  # exact duplicate of parent's
            (14998, "boundary-C", {"pod": "p1"}),  # only visible to the child
            (15500, "tail", {"pod": "p1"}),
        ]

        fake = _RecordingFakeLogAPI({
            (0, 20000): _loki_response(parent_entries),
            (14998, 20000): _loki_response(child_entries),
        })

        outpath = os.path.join(tmpdir, "boundary_out.txt")
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            self.assertRaises(SystemExit) as cm,
        ):
            fetch_logs_adaptive_parallel(
                None, "job-1", None, None, "", 0, 20000, 4, False, outpath
            )
        self.assertEqual(cm.exception.code, 0)

        with open(outpath, encoding="utf-8") as f:
            content = f.read()

        self.assertEqual(content.count("boundary-A"), 1)
        self.assertEqual(content.count("boundary-B"), 1)
        self.assertEqual(content.count("boundary-C"), 1)


class TestAdaptiveSchedulerSinkFailure(unittest.TestCase):
    """Scheduler-level sink-failure/cancellation integrations that require
    real ThreadPoolExecutor concurrency (an already-in-flight request).
    Output-message content/formatting for sink failures lives in
    test_log_adaptive_output.py's TestSinkFailureOutputMessages.
    """

    def test_real_fetch_log_unit_blocked_request_bounds_shutdown_and_uses_adaptive_timeout(
        self,
    ):
        """Exercises the REAL `_fetch_log_unit` (only `get_log` is mocked) so
        a regression in the `timeout=_ADAPTIVE_FETCH_TIMEOUT_SEC` wiring is
        detectable, and proves shutdown stays bounded by the in-flight
        request's own duration after cancellation."""
        UNIT_LOW, UNIT_BLOCK, block_duration, block_started = (
            _two_unit_cancellation_fixture()
        )

        class _BlockingFakeLogAPI:
            def __init__(self):
                self.calls = []
                self.lock = threading.Lock()

            def get_log(self, **kwargs):
                key = (kwargs.get("start"), kwargs.get("end"))
                with self.lock:
                    self.calls.append(dict(kwargs))
                if key == UNIT_LOW:
                    assert block_started.wait(timeout=5), "UNIT_BLOCK never started"
                    return _loki_response([(1, "low", {})])
                if key == UNIT_BLOCK:
                    # Simulates a worker blocked mid-HTTP-request, bounded by
                    # whatever `timeout` `_fetch_log_unit` actually passed
                    # through -- this is the real production call path.
                    block_started.set()
                    time.sleep(block_duration)
                    return _loki_response([(150, "blocked", {})])
                raise AssertionError(f"unexpected unit range {key}")

        fake = _BlockingFakeLogAPI()

        # A genuinely, permanently broken pipe fails on every print, not
        # just the first -- this also makes the BrokenPipeError propagation
        # path below deterministic to test.
        def flaky_print(*args, **kwargs):
            raise BrokenPipeError("broken pipe")

        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.console, "print", side_effect=flaky_print),
        ):
            sched = _AdaptiveLogScheduler(
                None, "job-1", None, None, "", UNIT_LOW[0], UNIT_LOW[1], 2, True, None
            )
            heapq.heappush(sched.pending, WorkUnit(sched._next_seq(), *UNIT_BLOCK))

            start_perf = time.perf_counter()
            with self.assertRaises(BrokenPipeError):
                sched.run()
            elapsed = time.perf_counter() - start_perf

        self.assertGreaterEqual(elapsed, block_duration)
        self.assertLess(elapsed, 5.0)
        self.assertFalse(sched.pending)

        # The real `_fetch_log_unit` must have reached `get_log` with the
        # bounded adaptive timeout for both units, including the one that
        # was genuinely in-flight when cancellation happened.
        calls_by_range = {(c["start"], c["end"]): c for c in fake.calls}
        self.assertIn(UNIT_LOW, calls_by_range)
        self.assertIn(UNIT_BLOCK, calls_by_range)
        self.assertEqual(
            calls_by_range[UNIT_LOW]["timeout"], log_mod._ADAPTIVE_FETCH_TIMEOUT_SEC
        )
        self.assertEqual(
            calls_by_range[UNIT_BLOCK]["timeout"], log_mod._ADAPTIVE_FETCH_TIMEOUT_SEC
        )


class TestAdaptiveSchedulerRetryFailureSurfaced(unittest.TestCase):
    def test_partial_failure_after_retries_exits_2_and_still_emits_others(self):
        # unit=[0, 20000) split into two children (saturation before
        # fetched_mid). One child permanently fails; the other succeeds.
        first_page = [(t, f"l{t}", {}) for t in range(0, 10000)]
        mid = 9999 + (20000 - 9999) // 2
        fake = _RecordingFakeLogAPI({
            (0, 20000): _loki_response(first_page),
            (9999, mid): RuntimeError("permanent"),
            (mid, 20000): _loki_response([(18000, "ok", {})]),
        })

        outpath = os.path.join(tmpdir, "partial_fail_out.txt")
        # The scheduler always supplies a real `cancelled` threading.Event to
        # `_fetch_log_unit`, so its backoff/retry sleeps go
        # through `_interruptible_sleep(delay, cancelled)`, not
        # `time.sleep(delay)` directly -- patch `_interruptible_sleep` itself
        # rather than `threading.Event.wait`, which `threading.Thread.start()`
        # also relies on internally and would break the executor's own
        # worker threads if patched process-wide.
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod, "_interruptible_sleep", return_value=None),
            self.assertRaises(SystemExit) as cm,
        ):
            fetch_logs_adaptive_parallel(
                None, "job-1", None, None, "", 0, 20000, 4, True, outpath
            )

        self.assertEqual(cm.exception.code, 2)
        with open(outpath, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("ok", content)
        # The permanently-failing child was retried the full budget.
        failing_calls = [c for c in fake.calls if (c["start"], c["end"]) == (9999, mid)]
        self.assertEqual(len(failing_calls), 5)


class TestWorkUnitHeapOrdering(unittest.TestCase):
    """`WorkUnit`'s `(start, seq_id)` total order makes it
    usable directly as a `heapq` key.
    """

    def test_smallest_start_dispatched_first_regardless_of_insertion_order(self):
        pending = []
        heapq.heappush(pending, WorkUnit(0, 5000, 6000))
        heapq.heappush(pending, WorkUnit(1, 1000, 2000))
        heapq.heappush(pending, WorkUnit(2, 3000, 4000))
        popped = heapq.heappop(pending)
        self.assertEqual((popped.start, popped.seq_id), (1000, 1))

    def test_equal_start_tie_broken_by_seq_id_ascending(self):
        pending = []
        heapq.heappush(pending, WorkUnit(7, 2000, 3000))
        heapq.heappush(pending, WorkUnit(3, 2000, 3000))
        first = heapq.heappop(pending)
        second = heapq.heappop(pending)
        self.assertEqual(first.seq_id, 3)
        self.assertEqual(second.seq_id, 7)

    def test_dynamically_enqueued_child_dispatched_by_start_not_insertion_order(self):
        """`--workers 1` (via `fetch_logs_adaptive_parallel` directly, no CLI
        layer needed) makes dispatch order directly observable one call at
        a time. Root splits (two-child, early saturation) into
        C1=[T,split_mid), C2=[split_mid,E) -- inserted in that order. C1
        itself then splits (late saturation, single unsplit child) into
        C1'=[T2,split_mid), which is *inserted after* C2 (already pending)
        but has a *smaller* start than C2. A min-heap must dispatch C1'
        next (smallest start); a plain FIFO queue would dispatch C2 next
        (inserted first) -- the case that distinguishes heap order from
        insertion order for a unit that didn't even exist at the time its
        sibling was enqueued.
        """
        S, E = 0, 4_000_000
        T = S + 1_000_000  # < branch_mid=S+2_000_000 -> two-child split
        split_mid = T + (E - T) // 2
        self.assertEqual(split_mid, S + 2_500_000)
        c1_start, c1_end = T, split_mid
        c2_start, c2_end = split_mid, E

        root_page = _pad_entries(10000, S, T, "root")
        # C1 saturates late (T2 >= its own branch_mid=S+1_750_000) -> a
        # single unsplit child C1'=[T2, c1_end).
        T2 = S + 2_300_000
        self.assertGreaterEqual(T2, (c1_start + c1_end) / 2)
        c1_page = _pad_entries(10000, c1_start, T2, "c1")
        c1_prime = (T2, c1_end)

        fake = _RecordingFakeLogAPI({
            (S, E): _loki_response(root_page),
            (c1_start, c1_end): _loki_response(c1_page),
            c1_prime: _loki_response([(T2 + 5, "c1-prime", {})]),
            (c2_start, c2_end): _loki_response([(c2_start + 5, "c2", {})]),
        })

        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            self.assertRaises(SystemExit) as cm,
            patch.object(log_mod.console, "print"),
        ):
            fetch_logs_adaptive_parallel(
                None, "job-1", None, None, "", S, E, 1, True, None
            )

        self.assertEqual(cm.exception.code, 0)
        actual = [(c["start"], c["end"]) for c in fake.calls]
        heap_order = [(S, E), (c1_start, c1_end), c1_prime, (c2_start, c2_end)]
        fifo_order = [(S, E), (c1_start, c1_end), (c2_start, c2_end), c1_prime]
        self.assertEqual(actual, heap_order)
        self.assertNotEqual(actual, fifo_order)


class TestSharedRateLimitSignalReducesConcurrency(unittest.TestCase):
    """Drives `_AdaptiveLogScheduler` directly, never through Click/CliRunner.

    Proves the rate-limit admission policy: a 429 activates the shared
    `_RateLimitSignal`, no new units are admitted while it is active,
    already-in-flight work is allowed to finish rather than being aborted,
    and admission resumes once the cooldown genuinely elapses.

    `test_429_signal_blocks_admission_until_cooldown_ends_event_driven`
    below is the sole (and deterministic) proof of this policy: it drives
    the real `_AdaptiveLogScheduler`/`_RateLimitSignal` (including a real
    `ThreadPoolExecutor`, via `sched.run()`) with controlled fake fetch
    functions synchronized via `threading.Event`s, and asserts directly on
    recorded submission timestamps and the signal's own `active()` state --
    never on a real-time sleep-and-compare window. Real-`ThreadPoolExecutor`
    concurrency is separately covered by `TestWorkerConcurrency` in
    test_log_cli.py.
    """

    def test_429_signal_blocks_admission_until_cooldown_ends_event_driven(self):
        """Drives the real `_AdaptiveLogScheduler`/`_RateLimitSignal`
        directly (via a controlled `log_mod._fetch_log_unit` fake),
        `--workers 2`, four hand-seeded units: TRIGGER=(0,1) signals the
        rate limit then resolves quickly; RUNNING=(1,2) runs concurrently
        with TRIGGER and blocks on a test-controlled event, standing in for
        already-in-flight work; LATER1=(2,3)/LATER2=(3,4) are only
        reachable once a worker slot frees. Proves: a 429 activates the
        signal and blocks new admission even with a free slot, already-
        started work (RUNNING) is allowed to finish rather than being
        aborted, and admission resumes (LATER1/LATER2 dispatched) only
        after the cooldown has genuinely elapsed and RUNNING is released.
        """
        # Generous relative to ordinary thread-scheduling/GIL jitter between
        # `trigger_done` firing and the "still active" check just after it,
        # so the test fails only on a genuine admission-control regression,
        # never on scheduling noise.
        cooldown = 1.0
        S = 1_700_000_000_000_000_000  # arbitrary ns epoch base
        TRIGGER = (S + 0, S + 1)
        RUNNING = (S + 1, S + 2)
        LATER1 = (S + 2, S + 3)
        LATER2 = (S + 3, S + 4)

        trigger_started = threading.Event()
        trigger_done = threading.Event()
        running_started = threading.Event()
        running_release = threading.Event()

        events: list = []  # (label, time.monotonic()) in call order
        events_lock = threading.Lock()

        def record(label):
            with events_lock:
                events.append((label, time.monotonic()))

        def fake_fetch(
            deployment,
            job,
            replica,
            job_history_name,
            query,
            start,
            end,
            limit,
            cancelled,
            rate_limit_signal,
        ):
            key = (start, end)
            if key == TRIGGER:
                record("trigger_start")
                trigger_started.set()
                # Explicit synchronization (not a timing guess): wait for
                # RUNNING to have genuinely started before signaling the
                # rate limit, so both units are provably admitted/in-flight
                # concurrently under `--workers 2` before the signal ever
                # activates -- otherwise TRIGGER (which does no I/O) could
                # race ahead and signal before the scheduler's `_submit_ready`
                # loop has even reached its second admission check.
                self.assertTrue(
                    running_started.wait(timeout=5), "RUNNING never started"
                )
                rate_limit_signal.signal(cooldown)
                result = FetchUnitResult(
                    [LogEntry((), start, "trigger", ())], False, start, start, False
                )
                record("trigger_end")
                trigger_done.set()
                return result
            if key == RUNNING:
                record("running_start")
                running_started.set()
                # Already in flight when the signal activates -- must be
                # allowed to run to completion, not aborted.
                finished_cleanly = running_release.wait(timeout=5)
                record("running_end")
                return FetchUnitResult(
                    [LogEntry((), start, "running", ())],
                    False,
                    start,
                    start,
                    not finished_cleanly,  # failed=True only if we timed out
                )
            if key in (LATER1, LATER2):
                record(f"later_start:{key}")
                return FetchUnitResult(
                    [LogEntry((), start, "later", ())], False, start, start, False
                )
            raise AssertionError(f"unexpected unit range {key}")

        with (
            patch.object(log_mod, "_fetch_log_unit", fake_fetch),
            patch.object(log_mod.console, "print"),
        ):
            sched = _AdaptiveLogScheduler(
                None, "job-1", None, None, "", TRIGGER[0], LATER2[1], 2, True, None
            )
            sched.pending = []
            for key in (TRIGGER, RUNNING, LATER1, LATER2):
                heapq.heappush(sched.pending, WorkUnit(sched._next_seq(), *key))

            run_thread_exit = {}

            def run_thread():
                try:
                    sched.run()
                except SystemExit as e:
                    run_thread_exit["code"] = e.code

            thread = threading.Thread(target=run_thread)
            thread.start()

            self.assertTrue(trigger_started.wait(timeout=5), "TRIGGER never started")
            self.assertTrue(running_started.wait(timeout=5), "RUNNING never started")

            # TRIGGER resolves quickly on its own (no artificial delay) and
            # frees a worker slot while RUNNING is still blocked and the
            # signal is active. Once its future has genuinely resolved,
            # give the scheduler's single dispatch thread a bounded, well
            # under-cooldown margin to run its next `_submit_ready` pass
            # (triggered by that resolution), then confirm it admitted
            # nothing -- the signal (activated by TRIGGER, cooldown=0.2s)
            # is still active at this point.
            self.assertTrue(trigger_done.wait(timeout=5), "TRIGGER never finished")
            self.assertTrue(sched.rate_limit_signal.active())
            time.sleep(0.1)

            with events_lock:
                later_events = [
                    label for label, _ in events if label.startswith("later_start:")
                ]
            self.assertEqual(
                later_events,
                [],
                "LATER1/LATER2 must not be dispatched while the rate-limit"
                f" signal is active: {events}",
            )
            self.assertFalse(
                running_release.is_set(),
                "RUNNING must still be genuinely in flight (not aborted) at this point",
            )

            # Wait out the real cooldown before releasing RUNNING, so that
            # when RUNNING's future resolves and `_submit_ready` runs again,
            # the signal has genuinely gone inactive.
            cooldown_deadline = time.monotonic() + cooldown + 0.1
            while time.monotonic() < cooldown_deadline:
                time.sleep(0.01)
            self.assertFalse(
                sched.rate_limit_signal.active(),
                "cooldown should have elapsed by now",
            )
            release_time = time.monotonic()
            running_release.set()

            thread.join(timeout=10)
            self.assertFalse(thread.is_alive(), "scheduler thread never finished")

        self.assertEqual(run_thread_exit.get("code"), 0)

        with events_lock:
            later_start_times = {
                label: t for label, t in events if label.startswith("later_start:")
            }
        self.assertEqual(len(later_start_times), 2, events)
        for label, t in later_start_times.items():
            self.assertGreaterEqual(
                t,
                release_time,
                f"{label} was dispatched before RUNNING was released: {events}",
            )


class TestJitteredBackoffNotIdenticalAcrossWorkers(unittest.TestCase):
    """Four independent, concurrently-dispatchable leaf units (hand-seeded,
    no bisection needed) driven through the real
    `_AdaptiveLogScheduler.run()` with `--workers 4`; only real
    `ThreadPoolExecutor` concurrency matters here, not the CLI layer.
    """

    def _run_with_script(self, leaves, script):
        fake = _RecordingFakeLogAPI(script)
        recorded = []

        def recording_sleep(d, c=None):
            recorded.append(d)

        _wait_for_quiescent_threads()
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod, "_interruptible_sleep", side_effect=recording_sleep),
            patch.object(log_mod.console, "print"),
            self.assertRaises(SystemExit) as cm,
        ):
            sched = _AdaptiveLogScheduler(
                None, "job-1", None, None, "", 0, 4000, 4, True, None
            )
            sched.pending = []
            for key in leaves:
                heapq.heappush(sched.pending, WorkUnit(sched._next_seq(), *key))
            sched.run()
        self.assertEqual(cm.exception.code, 0)
        return recorded

    def test_no_retry_after_uses_jittered_backoff_differing_per_worker(self):
        leaves = [(0, 100), (1000, 1100), (2000, 2100), (3000, 3100)]
        script = {
            key: [
                LogAPIError("rate limited", 429, retry_after=None),
                _loki_response([(key[0] + 1, "leaf", {})]),
            ]
            for key in leaves
        }
        recorded = self._run_with_script(leaves, script)
        # One 429 backoff sleep per leaf unit, each within attempt 0's
        # jittered range. `_interruptible_sleep` is a single process-wide
        # module attribute, so patching it also captures the scheduler's own
        # unrelated internal orchestration-loop waits (if any); those fall
        # well outside this narrow jitter window and are filtered out here
        # rather than asserting on the raw, unfiltered call list.
        jitter_calls = [d for d in recorded if 1.0 <= d < 1.5]
        self.assertEqual(len(jitter_calls), 4, f"all recorded calls: {recorded}")
        self.assertGreater(
            len(set(jitter_calls)),
            1,
            "expected jitter to differentiate concurrent workers' delays, got"
            f" {jitter_calls}",
        )

    def test_control_non_429_failure_uses_identical_fixed_delay(self):
        """Parallel control fixture: the same 4 leaves failing with a
        non-429 exception always sleep exactly the fixed 1.0s backoff --
        proving the jittered, non-identical values above come from the 429
        branch specifically, not from generic retry variance.
        """
        leaves = [(0, 100), (1000, 1100), (2000, 2100), (3000, 3100)]
        script = {
            key: [RuntimeError("boom"), _loki_response([(key[0] + 1, "leaf", {})])]
            for key in leaves
        }
        recorded = self._run_with_script(leaves, script)
        fixed_backoff_calls = [d for d in recorded if d == 1.0]
        self.assertEqual(len(fixed_backoff_calls), 4, f"all recorded calls: {recorded}")
        # None of the jitter branch's [1.0, 1.5) values (other than 1.0
        # itself) appear -- confirming this control never took the 429 path.
        self.assertFalse(any(1.0 < d < 1.5 for d in recorded))


class TestMalformedResponseNeverMisreportedAsSinkFailure(unittest.TestCase):
    """A stream label/metadata value that isn't a hashable scalar (or a
    non-string line) would make the resulting `LogEntry` unhashable and only
    fail later at the scheduler's flush-time dedup (`seen.add(entry)`),
    misreported to the user as a sink failure ("Failed to write logs")
    instead of the actual malformed-response root cause. This end-to-end
    message-classification distinction is the actual regression -- rejected
    at parse time, retried like any other malformed response, and reported
    as a normal fetch-retry failure, never a sink failure.
    """

    def _run(self, response):
        fake = _RecordingFakeLogAPI({(0, 100): response})
        printed = []

        def fake_print(*args, **kwargs):
            printed.append(str(args[0]) if args else "")

        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.time, "sleep", return_value=None),
            patch.object(log_mod.console, "print", side_effect=fake_print),
            self.assertRaises(SystemExit) as cm,
        ):
            fetch_logs_adaptive_parallel(
                None, "job-1", None, None, "", 0, 100, 4, True, None
            )
        return cm.exception.code, len(fake.calls), "\n".join(printed)

    def test_unhashable_or_malformed_line_values_retried_never_reported_as_sink_failure(
        self,
    ):
        cases = {
            "unhashable stream label": {
                "data": {
                    "result": [{
                        "stream": {"pod": ["not", "hashable"]},
                        "values": [["1", "line"]],
                    }]
                }
            },
            "unhashable metadata value": {
                "data": {
                    "result": [{
                        "stream": {"pod": "p1"},
                        "values": [["1", "line", {"k": {"nested": 1}}]],
                    }]
                }
            },
            "non-string line value": {
                "data": {
                    "result": [{"stream": {"pod": "p1"}, "values": [["1", 12345]]}]
                }
            },
        }
        for description, response in cases.items():
            with self.subTest(description=description):
                exit_code, call_count, output = self._run(response)
                self.assertEqual(exit_code, 2)
                self.assertEqual(call_count, 5)
                normalized = " ".join(output.split())
                self.assertIn("could not be fetched after 5 retries", normalized)
                self.assertNotIn("Failed to write logs", normalized)


class TestOversizedPageCappingIntegration(unittest.TestCase):
    """End-to-end (not just the capping mechanic tested at the
    `_fetch_log_unit` layer by TestFetchLogUnitOversizedPageCapping above):
    with the real `_ADAPTIVE_PAGE_LIMIT` (10000, no monkeypatching), a
    14000-entry oversized root page must be capped, its child re-fetched,
    the trace diagnostic must name both the original count and the cap, and
    the final total must still count all 14000 distinct entries once the
    child is fetched.
    """

    def test_oversized_backend_page_is_capped_and_child_recovers_the_rest(self):
        # A small, dedicated [S, E) span (all 14000 offsets fit inside it)
        # chosen so branch_mid=(S+E)/2 <= T=S+9999 -- i.e. so the capped
        # saturation takes the single-unsplit-child branch, keeping this
        # test's expected call sequence to exactly two calls and focused on
        # capping, not also re-proving the branch-decision math covered
        # elsewhere.
        S, E = 0, 16000
        entries = [(S + i, f"e{i}", {}) for i in range(14000)]
        T = S + 9999  # the capped set's max_ts: the 10000 smallest of 14000
        child_entries = [(S + i, f"e{i}", {}) for i in range(9999, 14000)]
        fake = _RecordingFakeLogAPI({
            (S, E): _loki_response(entries),
            (T, E): _loki_response(child_entries),
        })

        records = []
        handler_id = logger.add(
            lambda msg: records.append(msg.record["message"]), level="TRACE"
        )
        outpath = os.path.join(tmpdir, "oversized_cap_out.txt")
        try:
            with (
                patch.object(log_mod, "APIClient", _make_client_class(fake)),
                self.assertRaises(SystemExit) as cm,
            ):
                fetch_logs_adaptive_parallel(
                    None, "job-1", None, None, "", S, E, 4, True, outpath
                )
        finally:
            logger.remove(handler_id)

        self.assertEqual(cm.exception.code, 0)
        requested = [(c["start"], c["end"]) for c in fake.calls]
        self.assertEqual(requested, [(S, E), (T, E)])
        self.assertTrue(
            any("14000" in rec and "10000" in rec for rec in records),
            "expected a trace record naming original count 14000 and cap"
            f" 10000, got: {records}",
        )
        with open(outpath, encoding="utf-8") as f:
            lines = f.read().splitlines()
        for i in (0, 3500, 9999, 13999):
            self.assertEqual(sum(1 for ln in lines if ln.endswith(f"e{i}")), 1)
        self.assertIn("total 14000 lines", lines[-1])


class TestBranchMidTrueDivision(unittest.TestCase):
    """Odd-sum interval boundary."""

    def test_odd_sum_interval_uses_true_division_two_child_branch(self):
        sched = _AdaptiveLogScheduler(
            None, "job-1", None, None, "", 0, 2001, 4, True, None
        )
        sched.pending = []  # drop the constructor-seeded unit; test only the split
        unit = WorkUnit(sched._next_seq(), 0, 2001)
        result = FetchUnitResult(
            entries=[LogEntry((), 1000, "x", ())],
            saturated=True,
            min_ts=0,
            max_ts=1000,
            failed=False,
        )
        sched._handle_result(unit, result)
        ranges = sorted((u.start, u.end) for u in sched.pending)
        # branch_mid = 2001 / 2 = 1000.5 (true division); T=1000 < 1000.5, so
        # the two-child branch is taken: [1000, 1500) and [1500, 2001) --
        # never the single unsplit [1000, 2001) a floor-division
        # branch_mid == 1000 would have produced (T >= branch_mid).
        self.assertEqual(ranges, [(1000, 1500), (1500, 2001)])


class TestWatermarkRegressionFailFast(unittest.TestCase):
    """A watermark regression is a handled
    failure (test-only fault injection, since this cannot occur in
    practice), never an uncaught `AssertionError`.
    """

    def test_forced_watermark_regression_exits_1_with_scheduling_error_message(self):
        fake = _RecordingFakeLogAPI({(0, 100): _loki_response([(1, "a", {})])})
        printed = []

        def fake_print(*args, **kwargs):
            printed.append(args[0] if args else "")

        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.console, "print", side_effect=fake_print),
            patch.object(
                log_mod._AdaptiveLogScheduler, "_compute_watermark", return_value=-1
            ),
            self.assertRaises(SystemExit) as cm,
        ):
            fetch_logs_adaptive_parallel(
                None, "job-1", None, None, "", 0, 100, 4, True, None
            )
        self.assertEqual(cm.exception.code, 1)
        self.assertTrue(any("Internal scheduling error" in p for p in printed), printed)

    def test_watermark_regression_error_is_distinct_from_sink_failure_message(self):
        # Same fault injection, but confirm the message does NOT read like a
        # sink-write failure (they share the fail-fast/exit-1 contract but
        # must be distinguishable to the user).
        fake = _RecordingFakeLogAPI({(0, 100): _loki_response([(1, "a", {})])})
        printed = []

        def fake_print(*args, **kwargs):
            printed.append(args[0] if args else "")

        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.console, "print", side_effect=fake_print),
            patch.object(
                log_mod._AdaptiveLogScheduler, "_compute_watermark", return_value=-1
            ),
            self.assertRaises(SystemExit),
        ):
            fetch_logs_adaptive_parallel(
                None, "job-1", None, None, "", 0, 100, 4, True, None
            )
        self.assertFalse(any("Failed to write logs" in p for p in printed))


class TestSameTimestampCaseBContinuation(unittest.TestCase):
    """Case B: a saturated page that entirely shares
    `timestamp_ns == T`, with `T + 1 < unit.end`, must enqueue exactly one
    child `[T + 1, unit.end)` -- not zero children (Case A's terminal
    behavior) and not a two-child bisection of `[T, unit.end)`.
    """

    def test_handle_result_enqueues_single_t_plus_one_child(self):
        sched = log_mod._AdaptiveLogScheduler(
            None, "job-1", None, None, "", 0, 100000, 4, True, None
        )
        sched.pending = []  # drop the constructor-seeded unit
        unit = WorkUnit(sched._next_seq(), 0, 100000)
        # Every entry in the saturated page shares timestamp_ns == T == 500,
        # and T + 1 (501) is far below unit.end (100000) -- Case B applies.
        result = FetchUnitResult(
            entries=[LogEntry((), 500, "dup", ())],
            saturated=True,
            min_ts=500,
            max_ts=500,
            failed=False,
        )
        progress_advance = sched._handle_result(unit, result)
        self.assertFalse(progress_advance)
        self.assertEqual(len(sched.pending), 1)
        child = sched.pending[0]
        self.assertEqual((child.start, child.end), (501, 100000))

    def test_case_a_terminal_enqueues_no_children_even_when_min_ts_equals_t(self):
        # Contrast fixture: T >= unit.end - 1 (Case A) must win even though
        # min_ts == T would otherwise also satisfy Case B's condition --
        # Case A is checked first and always takes priority.
        sched = log_mod._AdaptiveLogScheduler(
            None, "job-1", None, None, "", 0, 501, 4, True, None
        )
        sched.pending = []
        unit = WorkUnit(sched._next_seq(), 0, 501)
        result = FetchUnitResult(
            entries=[LogEntry((), 500, "dup", ())],
            saturated=True,
            min_ts=500,
            max_ts=500,  # T=500 >= unit.end(501) - 1 -> Case A
            failed=False,
        )
        progress_advance = sched._handle_result(unit, result)
        self.assertTrue(progress_advance)
        self.assertEqual(sched.pending, [])

    def test_case_a_duplicated_entries_survive_dedup_end_to_end(self):
        """Case A (terminal, 1ns remainder): unlike
        `test_case_a_terminal_enqueues_no_children_even_when_min_ts_equals_t`
        above (which only checks the branching decision via a direct
        `_handle_result` call), this drives the real end-to-end path with
        every line duplicated in the raw response -- proving flush-time
        dedup, not just the child-count decision, on the terminal Case A
        path: each *distinct* line still survives exactly once despite
        10000 raw (5000 distinct x2) entries, and no further request is
        ever made.
        """
        S, E = 0, 2
        T = E - 1  # remaining range [T, E) is exactly 1ns wide
        entries = []
        for i in range(5000):
            entries.append((T, f"same-ts-{i}", {}))
            entries.append((T, f"same-ts-{i}", {}))
        self.assertEqual(len(entries), 10000)
        fake = _RecordingFakeLogAPI({(S, E): _loki_response(entries)})
        outpath = os.path.join(tmpdir, "case_a_dedup_out.txt")

        records = []
        handler_id = logger.add(
            lambda msg: records.append(msg.record["message"]), level="TRACE"
        )
        try:
            with (
                patch.object(log_mod, "APIClient", _make_client_class(fake)),
                self.assertRaises(SystemExit) as cm,
            ):
                fetch_logs_adaptive_parallel(
                    None, "job-1", None, None, "", S, E, 4, True, outpath
                )
        finally:
            logger.remove(handler_id)

        self.assertEqual(cm.exception.code, 0)
        # No children: only the one saturated request was ever made.
        self.assertEqual(len(fake.calls), 1)
        with open(outpath, encoding="utf-8") as f:
            lines = f.read().splitlines()
        for i in (0, 1, 2499, 4999):
            self.assertEqual(sum(1 for ln in lines if ln.endswith(f"same-ts-{i}")), 1)
        # A trace diagnostic mentioning the same-timestamp safeguard was
        # emitted, and it must be Case A's terminal message, not Case B's
        # "continuing scan at T+1".
        same_ts_records = [rec for rec in records if "same-timestamp" in rec]
        self.assertTrue(
            same_ts_records,
            f"expected a same-timestamp safeguard trace record, got: {records}",
        )
        self.assertTrue(
            any("incomplete" in rec for rec in same_ts_records), same_ts_records
        )
        self.assertFalse(
            any("continuing scan at T+1" in rec for rec in same_ts_records),
            same_ts_records,
        )

    def test_case_b_duplicated_entries_survive_dedup_end_to_end(self):
        """Case B, end-to-end, with every same-timestamp line duplicated in
        the raw response: flush-time dedup survives alongside the later,
        genuinely distinct record fetched by the `[T+1, E)` child, and the
        Case B trace diagnostic is emitted.
        """
        S, E = 0, 100000
        T = 1500
        entries = []
        for i in range(5000):
            entries.append((T, f"same-ts-{i}", {}))
            entries.append((T, f"same-ts-{i}", {}))
        self.assertEqual(len(entries), 10000)
        later_entry = _loki_response([(T + 2000, "later-distinct", {})])
        fake = _RecordingFakeLogAPI({
            (S, E): _loki_response(entries),
            (T + 1, E): later_entry,
        })
        outpath = os.path.join(tmpdir, "case_b_dedup_out.txt")

        records = []
        handler_id = logger.add(
            lambda msg: records.append(msg.record["message"]), level="TRACE"
        )
        try:
            with (
                patch.object(log_mod, "APIClient", _make_client_class(fake)),
                self.assertRaises(SystemExit) as cm,
            ):
                fetch_logs_adaptive_parallel(
                    None, "job-1", None, None, "", S, E, 4, True, outpath
                )
        finally:
            logger.remove(handler_id)

        self.assertEqual(cm.exception.code, 0)
        # Exactly one child at [T+1, E) -- never [T, E), never a two-child
        # bisection.
        requested = {(c["start"], c["end"]) for c in fake.calls}
        self.assertEqual(requested, {(S, E), (T + 1, E)})
        with open(outpath, encoding="utf-8") as f:
            lines = f.read().splitlines()
        for i in (0, 1, 2499, 4999):
            self.assertEqual(sum(1 for ln in lines if ln.endswith(f"same-ts-{i}")), 1)
        self.assertEqual(sum(1 for ln in lines if ln.endswith("later-distinct")), 1)
        same_ts_records = [rec for rec in records if "same-timestamp" in rec]
        self.assertTrue(
            any("continuing scan at T+1" in rec for rec in same_ts_records),
            same_ts_records,
        )


class TestAdaptivePageLimitConstantUsed(unittest.TestCase):
    """`_ADAPTIVE_PAGE_LIMIT` (10000) must be the actual page size used by
    the adaptive path everywhere it previously hardcoded 5000: the
    `_fetch_log_unit` default parameter and the scheduler's explicit
    `limit=` submission.
    """

    def test_constant_value_is_10000(self):
        self.assertEqual(log_mod._ADAPTIVE_PAGE_LIMIT, 10000)

    def test_fetch_log_unit_default_limit_is_the_named_constant(self):
        import inspect

        sig = inspect.signature(_fetch_log_unit)
        self.assertEqual(sig.parameters["limit"].default, log_mod._ADAPTIVE_PAGE_LIMIT)

    def test_scheduler_submits_with_the_named_constant_as_limit(self):
        # A page just under 10000 entries must NOT saturate (proving the
        # scheduler's live per-request limit is 10000, not the old 5000).
        entries = [(t, f"l{t}", {}) for t in range(9999)]
        fake = _RecordingFakeLogAPI({(0, 100000): _loki_response(entries)})
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            self.assertRaises(SystemExit) as cm,
            patch.object(log_mod.console, "print"),
        ):
            fetch_logs_adaptive_parallel(
                None, "job-1", None, None, "", 0, 100000, 4, True, None
            )
        self.assertEqual(cm.exception.code, 0)
        # No saturation -> no split -> exactly one request was ever made.
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.calls[0]["limit"], 10000)


class TestDeadlockAvoidanceFrontierExemption(unittest.TestCase):
    """Regression test for the rejected blanket-gate admission-control
    design's confirmed deadlock.

    Fixture: `--workers 4`, `_ADAPTIVE_PAGE_LIMIT` patched to 4, so
    `_max_buffered_entries == (4 + 1) * 4 == 20`. The frontier (root) unit
    blocks until released; siblings A/B/C resolve without blocking,
    contributing 4/4/5 entries respectively -- all four (root/A/B/C) are
    admitted up front under 4 workers. A fourth unit D can only be popped
    once A/B/C are already popped (heap order); once A/B/C are in the
    buffer (`len(buffer) == 13`) with only root active, D's projected
    resident count (`13 + 2*4 == 21`) is one OVER cap (20), so the ordinary
    (`active >= 1`) admission path withholds it while root is active.

    Once root resolves, `self.active` becomes empty with `self.pending ==
    [D]`. Under the superseded blanket-gate design (no `len(active) >= 1`
    exemption), this is an unrecoverable deadlock -- nothing is ever
    dispatched again. The corrected `cap_blocks` (mandatory exemption when
    nothing is active) must dispatch D anyway, asserted via a wall-clock-
    bounded `join()` on a background thread running the real `run()` loop.
    """

    def test_frontier_exemption_prevents_deadlock_when_buffer_at_raw_cap(self):
        release_root = threading.Event()

        # Root is the constructor-seeded frontier unit -- wide range, held
        # "in flight" until explicitly released by the test, at which point
        # it resolves saturated (Case A terminal) contributing its own
        # block of entries.
        ROOT = (0, 5000)
        # Wide ranges so each saturated sibling's own entries land at a
        # timestamp *above* D's `start`, so they are never drained away by
        # an intervening watermark advance before the decisive
        # cap-at-capacity dispatch decision for D is made.
        SIB_A = (20, 3000)
        SIB_B = (30, 3100)
        SIB_C = (100, 4000)
        SIB_D = (1000, 1010)

        def fake_fetch(
            deployment,
            job,
            replica,
            job_history_name,
            query,
            start,
            end,
            limit,
            cancelled,
            rate_limit_signal,
        ):
            key = (start, end)
            if key == ROOT:
                release_root.wait(timeout=10)
                entries = [LogEntry((), 4999, f"r{i}", ()) for i in range(4)]
                return FetchUnitResult(entries, True, 4999, 4999, False)
            if key == SIB_A:
                entries = [LogEntry((), 2999, f"a{i}", ()) for i in range(4)]
                return FetchUnitResult(entries, True, 2999, 2999, False)
            if key == SIB_B:
                entries = [LogEntry((), 3099, f"b{i}", ()) for i in range(4)]
                return FetchUnitResult(entries, True, 3099, 3099, False)
            if key == SIB_C:
                entries = [LogEntry((), 3999, f"c{i}", ()) for i in range(5)]
                return FetchUnitResult(entries, True, 3999, 3999, False)
            if key == SIB_D:
                return FetchUnitResult(
                    [LogEntry((), 1005, "d0", ())], False, 1005, 1005, False
                )
            raise AssertionError(f"unexpected unit range {key}")

        outdir = tempfile.mkdtemp(dir=tmpdir)
        outpath = os.path.join(outdir, "deadlock_regression.txt")

        # Instrumentation: wrap the real (unpatched) `_submit_ready` to
        # record, for every unit it admits under real `ThreadPoolExecutor`
        # concurrency, the `active` count immediately before that unit's
        # admission and the buffer length at the start of the call (which
        # cannot change mid-call, since `_submit_ready` itself never
        # releases the GIL to do I/O). This lets the assertions below
        # distinguish ordinary (active >= 1) admissions -- which must
        # always respect the tightened cap -- from frontier (active == 0)
        # admissions, which are the sole permitted source of overage.
        submission_log = []
        real_submit_ready = _AdaptiveLogScheduler._submit_ready

        def instrumented_submit_ready(self, executor):
            before_futures = set(self.active.keys())
            pre_active = len(self.active)
            buffer_len_before = len(self.buffer)
            real_submit_ready(self, executor)
            running_active = pre_active
            for future, unit in self.active.items():
                if future in before_futures:
                    continue
                submission_log.append({
                    "range": (unit.start, unit.end),
                    "active_before": running_active,
                    "buffer_len_before": buffer_len_before,
                })
                running_active += 1

        with (
            patch.object(log_mod, "_ADAPTIVE_PAGE_LIMIT", 4),
            patch.object(log_mod, "_fetch_log_unit", fake_fetch),
            patch.object(
                _AdaptiveLogScheduler, "_submit_ready", instrumented_submit_ready
            ),
        ):
            sched = _AdaptiveLogScheduler(
                None, "job-1", None, None, "", ROOT[0], ROOT[1], 4, True, outpath
            )
            page_limit = log_mod._ADAPTIVE_PAGE_LIMIT
            cap = sched._max_buffered_entries
            self.assertEqual(cap, 20)  # (workers=4 + 1) * page_limit(4)
            heapq.heappush(sched.pending, WorkUnit(sched._next_seq(), *SIB_A))
            heapq.heappush(sched.pending, WorkUnit(sched._next_seq(), *SIB_B))
            heapq.heappush(sched.pending, WorkUnit(sched._next_seq(), *SIB_C))
            heapq.heappush(sched.pending, WorkUnit(sched._next_seq(), *SIB_D))

            result_holder = {}

            def run_in_thread():
                try:
                    sched.run()
                except SystemExit as e:
                    result_holder["exit_code"] = e.code

            t = threading.Thread(target=run_in_thread, daemon=True)
            t.start()

            # Poll (bounded, no fixed-delay guessing) for the deterministic
            # intermediate state: only root remains active/unresolved, D is
            # the sole remaining pending unit, and A/B/C have all already
            # been accounted for (in the buffer). This state is guaranteed
            # to be reached -- see the class docstring's arithmetic -- but
            # real-thread completion order/timing varies, so we wait for it
            # rather than assuming a fixed delay is long enough.
            reached_pre_release_state = False
            for _ in range(3000):
                if (
                    len(sched.active) == 1
                    and any((u.start, u.end) == ROOT for u in sched.active.values())
                    and [(u.start, u.end) for u in sched.pending] == [SIB_D]
                ):
                    reached_pre_release_state = True
                    break
                time.sleep(0.001)

            self.assertTrue(
                reached_pre_release_state,
                "scheduler never reached the expected pre-release state"
                f" (active={list(sched.active.values())},"
                f" pending={[(u.start, u.end) for u in sched.pending]})",
            )
            self.assertEqual(len(sched.buffer), 13)  # A(4) + B(4) + C(5)

            release_root.set()

            # A generous wall-clock bound: the corrected scheduler completes
            # promptly once released; a hang under the superseded
            # blanket-gate design would never return within this bound.
            t.join(timeout=10)

        self.assertFalse(
            t.is_alive(),
            "scheduler did not complete within the timeout -- this is the"
            " frontier-exemption deadlock regression",
        )
        self.assertEqual(result_holder.get("exit_code"), 0)

        with open(outpath, encoding="utf-8") as f:
            lines = f.read().splitlines()
        # Chronological, gap-free, duplicate-free output across all four
        # resolved units, including D (dispatched only via the frontier
        # exemption) and every saturated sibling.
        expected_order = (
            ["d0"]
            + [f"a{i}" for i in range(4)]
            + [f"b{i}" for i in range(4)]
            + [f"c{i}" for i in range(5)]
            + [f"r{i}" for i in range(4)]
        )
        self.assertEqual(lines[:18], expected_order)
        self.assertTrue(lines[18].startswith("Time range: UTC|"))
        self.assertIn("total 18 lines", lines[18])

        # Every ordinary (active >= 1) admission recorded under real
        # `ThreadPoolExecutor` concurrency must respect the tightened cap:
        # buffer + (active_before + 1) * page_limit <= cap. Any admission
        # that ever exceeds the cap must be a frontier (active_before == 0)
        # dispatch -- confirming the only permitted overage in this
        # scenario is the frontier case (ROOT and D), never an ordinary
        # submission being over-admitted.
        self.assertTrue(submission_log, "no submissions were recorded")
        frontier_ranges = set()
        for entry in submission_log:
            resident_after = (
                entry["buffer_len_before"] + (entry["active_before"] + 1) * page_limit
            )
            if entry["active_before"] == 0:
                frontier_ranges.add(entry["range"])
                continue
            self.assertLessEqual(
                resident_after,
                cap,
                f"ordinary submission {entry['range']} was admitted despite"
                " pushing the resident count over the cap"
                f" (log={submission_log})",
            )
        # ROOT and D are the only units ever dispatched while nothing was
        # active -- ROOT trivially (it's the very first submission, with an
        # empty buffer), and D specifically because A/B/C had already
        # driven the buffer to the raw cap, so only the frontier exemption
        # let it through.
        self.assertEqual(frontier_ranges, {ROOT, SIB_D})


class TestAdmissionControlFrontierExemption(unittest.TestCase):
    """The frontier (smallest-`start`) pending unit is admitted even when
    the buffer already sits at/over cap, as long as nothing is active --
    `len(self.active) >= 1` in `_admission_blocked` is mandatory, not an
    optimization. Real-thread coverage of this same exemption breaking an
    actual deadlock lives in
    `TestDeadlockAvoidanceFrontierExemption`; this test isolates the
    admission decision itself, deterministically.
    """

    def test_frontier_unit_admitted_despite_buffer_already_over_cap(self):
        with patch.object(log_mod, "_ADAPTIVE_PAGE_LIMIT", 4):
            page_limit = log_mod._ADAPTIVE_PAGE_LIMIT
            sched = _AdaptiveLogScheduler(
                None, "job-1", None, None, "", 0, 100000, 2, True, None
            )
            cap = sched._max_buffered_entries
            self.assertEqual(cap, 12)  # (workers=2 + 1) * page_limit(4)

            sched.pending = []
            sched.active = {}
            sched.buffer = [None] * (cap + page_limit)  # already well over cap
            frontier_unit = WorkUnit(sched._next_seq(), 0, 100)
            heapq.heappush(sched.pending, frontier_unit)

            admitted = []

            class _RecordingExecutor:
                def submit(self, fn, *args, **kwargs):
                    from concurrent.futures import Future

                    admitted.append(args)
                    return Future()

            sched._submit_ready(_RecordingExecutor())

            self.assertEqual(
                len(admitted),
                1,
                "the frontier unit must be admitted even with the buffer over cap",
            )
            self.assertEqual(len(sched.active), 1)
            self.assertEqual(sched.pending, [])


class TestAdmissionControlOrdinarySubmissionOffByOne(unittest.TestCase):
    """Regression test for `_submit_ready`'s `cap_blocks` comparison
    operator (`>` vs `>=`).

    The documented bound is "at or under the cap": an ordinary (active >= 1)
    submission must be ADMITTED whenever its proposed post-admission
    resident count (`len(buffer) + (len(active) + 1) * page_limit`) would
    land exactly AT the cap, and WITHHELD only when it would EXCEED the
    cap. A previous round used `>=` in `cap_blocks`, which wrongly withheld
    admission when the proposed count landed exactly at the cap -- e.g.
    with `--workers 2`, one page buffered and one worker active, admitting
    a second worker proposes exactly `3 * page_limit == cap`, which `>=`
    incorrectly blocked, silently serializing the scheduler to concurrency
    1. The fixed comparison (`>`) admits that case and only withholds a
    proposal that would actually exceed the cap.
    """

    def _make_scheduler(self, buffer_len):
        page_limit = log_mod._ADAPTIVE_PAGE_LIMIT
        sched = _AdaptiveLogScheduler(
            None, "job-1", None, None, "", 0, 100000, 3, True, None
        )
        cap = sched._max_buffered_entries
        self.assertEqual(cap, 16)  # (workers=3 + 1) * page_limit(4)

        sched.pending = []
        in_flight_unit = WorkUnit(sched._next_seq(), 5000, 6000)
        sched.active = {object(): in_flight_unit}
        sched.buffer = [None] * buffer_len

        next_unit = WorkUnit(sched._next_seq(), 0, 100)
        heapq.heappush(sched.pending, next_unit)
        return sched, cap, page_limit

    def test_proposed_count_landing_exactly_at_cap_is_admitted(self):
        # buffer + (active + 1) * page_limit == cap exactly -- the direct
        # regression case: this must be ADMITTED, not withheld.
        with patch.object(log_mod, "_ADAPTIVE_PAGE_LIMIT", 4):
            sched, cap, page_limit = self._make_scheduler(0)
            buffer_len = cap - 2 * page_limit  # + (1+1)*page_limit == cap
            sched.buffer = [None] * buffer_len
            self.assertEqual(
                len(sched.buffer) + (len(sched.active) + 1) * page_limit, cap
            )

            admitted = []

            class _RecordingExecutor:
                def submit(self, fn, *args, **kwargs):
                    from concurrent.futures import Future

                    admitted.append(args)
                    fut = Future()
                    return fut

            sched._submit_ready(_RecordingExecutor())

            self.assertEqual(
                len(admitted), 1, "landing exactly at cap must be admitted"
            )
            self.assertEqual(len(sched.active), 2)
            self.assertEqual(sched.pending, [])

    def test_proposed_count_exceeding_cap_is_withheld(self):
        # buffer + (active + 1) * page_limit == cap + 1 -- strictly over the
        # cap. This must remain withheld (unchanged behavior).
        with patch.object(log_mod, "_ADAPTIVE_PAGE_LIMIT", 4):
            sched, cap, page_limit = self._make_scheduler(0)
            buffer_len = cap - 2 * page_limit + 1
            sched.buffer = [None] * buffer_len
            self.assertEqual(
                len(sched.buffer) + (len(sched.active) + 1) * page_limit, cap + 1
            )

            class _RefusingExecutor:
                """Fails the test if a submission is admitted -- this is an
                ordinary (active >= 1) admission decision, so admitting one
                more unit here would push the true resident count over the
                cap, which must remain prevented.
                """

                def submit(self, *args, **kwargs):
                    raise AssertionError(
                        "an ordinary submission was admitted despite pushing"
                        " the resident count over the cap"
                    )

            sched._submit_ready(_RefusingExecutor())

            self.assertEqual(len(sched.active), 1, "no new unit should be admitted")
            self.assertEqual(
                [(u.start, u.end) for u in sched.pending],
                [(0, 100)],
                "the pending unit should remain withheld",
            )


if __name__ == "__main__":
    unittest.main()
