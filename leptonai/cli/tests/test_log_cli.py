"""Independent scenario/CLI-level tests for adaptive parallel log retrieval.

These tests drive `lep log get` end-to-end through `click.testing.CliRunner`,
exactly as a user would invoke it, with only `APIClient` replaced by a fake
that records every `client.log.get_log(...)` call and serves scripted Loki
`query_range`-shaped responses. They are not written from reading
`leptonai/cli/log.py`'s implementation logic.

Two small, pre-existing (and unmodified by this feature) helpers are used
directly to build fixtures/expected strings, the same way production code
uses them: `_preprocess_time` (parses `--start`/`--end` strings to ns epoch)
and `_epoch_to_time_str` (formats ns epoch back to the display string). Using
them is no different from a test calling `json.dumps` to build a fixture --
it does not encode any assertion about the adaptive scheduler's behavior.
"""

import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai, matching
# the existing CLI test suite convention (test_job_cli.py).
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import glob
import threading
import time
import unittest
from unittest.mock import patch

from click.testing import CliRunner

from leptonai.api.v2.log import LogAPI
from leptonai.cli import cli as cli_mod
from leptonai.cli import lep as cli
from leptonai.cli import log as log_mod
from leptonai.cli.log import _epoch_to_time_str, _preprocess_time
from leptonai.cli.tests._log_test_helpers import (
    InFlightTracker as _InFlightTracker,
    RealLogAPIHTTPClient as _RealLogAPIHTTPClient,
    loki_response as _loki_response,
    make_client_class as _make_client_class,
    pad_entries as _pad_entries,
)

# Captured before any test patches `log_mod.time.sleep` -- see
# `_log_test_helpers` for why a real reference must be kept separately.
_REAL_SLEEP = time.sleep


class _FakeLogAPI:
    """Fake `client.log`. Records every `get_log` call (including the
    one-record probe). Non-probe (limit != 1) calls are matched by
    (start, end) against `script`: a scripted response dict, an Exception
    (raised), or a list of either (consumed in call-index order, last one
    repeats)."""

    def __init__(self, script, probe_response=None, delay_fn=None, inflight=None):
        self.script = script
        self.probe_response = (
            probe_response
            if probe_response is not None
            else _loki_response([(1, "probe", {})])
        )
        self.calls = []
        self._counts = {}
        self.lock = threading.Lock()
        self.delay_fn = delay_fn
        self.inflight = inflight

    def get_log(self, **kwargs):
        if self.inflight is not None:
            self.inflight.enter()
        try:
            with self.lock:
                self.calls.append(dict(kwargs))
            if kwargs.get("limit") == 1:
                return self.probe_response
            key = (kwargs.get("start"), kwargs.get("end"))
            with self.lock:
                self._counts[key] = self._counts.get(key, 0) + 1
                n = self._counts[key]
            if self.delay_fn is not None:
                time.sleep(self.delay_fn(key))
            outcome = self.script.get(key)
            if isinstance(outcome, list):
                outcome = outcome[min(n - 1, len(outcome) - 1)]
            if isinstance(outcome, Exception):
                raise outcome
            if outcome is None:
                return {"data": {"result": []}}
            return outcome
        finally:
            if self.inflight is not None:
                self.inflight.leave()

    def unit_calls(self):
        """Calls made by the adaptive scheduler (always direction='forward'),
        excluding the one-record probe and any LEGACY-path calls."""
        return [c for c in self.calls if c.get("direction") == "forward"]


def _invoke(args, fake_log_api, input=None):
    runner = CliRunner()
    client_cls = _make_client_class(fake_log_api)
    # `lep`'s group callback calls check_lepton_version(), which makes a
    # real network call to pypi.org and prints a "newer version available"
    # banner to stdout when the installed version is behind -- a side
    # effect unrelated to the adaptive scheduler that would otherwise leak
    # non-deterministically into `result.output` (first invocation in a
    # fresh process vs. later ones once its own cache file is warm). Not a
    # bug in check_lepton_version itself; just needs to be inert here so
    # every CLI-level assertion in this file only reflects `log get`'s own
    # output.
    with (
        patch.object(log_mod, "APIClient", client_cls),
        patch.object(cli_mod, "check_lepton_version", return_value=None),
    ):
        result = runner.invoke(cli, args, input=input)
    return result, client_cls.last_instance


START_STR = "2024-01-01 00:00:00.000000"
END_STR = "2024-01-01 00:00:00.004000"
UNIX_START = _preprocess_time(START_STR, epoch=True)
UNIX_END = _preprocess_time(END_STR, epoch=True)
# --start/--end only support microsecond precision, so the parsed ns delta is
# 1000x the "004000" numeral in the string above.
assert UNIX_END - UNIX_START == 4_000_000

TREE_START_STR = "2024-01-01 00:00:00.000000"
TREE_END_STR = "2024-01-01 00:00:00.016000"
TREE_S = _preprocess_time(TREE_START_STR, epoch=True)
TREE_E = _preprocess_time(TREE_END_STR, epoch=True)
assert TREE_E - TREE_S == 16_000_000


def _base_args(*extra, start=START_STR, end=END_STR, target=("-e", "dep1")):
    return ["log", "get", *target, "--start", start, "--end", end, *extra]


def _build_tree_script():
    """3-leaf, 2-level bisecting tree over [TREE_S, TREE_E):

    root=[S, E) branch_mid=S+8000, saturates at T1=S+3000 (<mid) -> two
    children C1=[S+3000, S+9500), C2=[S+9500, E).
    C1 branch_mid=S+6250, saturates at T2=S+4000 (<mid) -> two children
    D1=[S+4000, S+6750), D2=[S+6750, S+9500).
    C2 terminates without further splitting.
    Leaves: D1, D2, C2 -- three leaf units at different recursion depths.
    """
    S, E = TREE_S, TREE_E
    root_page = _pad_entries(10000, S + 0, S + 3_000_000, "r")
    c1_page = _pad_entries(10000, S + 3_000_000, S + 4_000_000, "c1")
    d1_resp = _loki_response([(S + 4_500_000, "d1a", {}), (S + 4_600_000, "d1b", {})])
    d2_resp = _loki_response([(S + 7_000_000, "d2a", {})])
    c2_resp = _loki_response([(S + 12_000_000, "c2a", {})])
    script = {
        (S, E): _loki_response(root_page),
        (S + 3_000_000, S + 9_500_000): _loki_response(c1_page),
        (S + 4_000_000, S + 6_750_000): d1_resp,
        (S + 6_750_000, S + 9_500_000): d2_resp,
        (S + 9_500_000, E): c2_resp,
    }
    return script


# ---------------------------------------------------------------------------
# under-limit single unit
# ---------------------------------------------------------------------------


class TestUnderLimitSingleUnit(unittest.TestCase):
    def test_single_request_chronological_output(self):
        entries = [
            (UNIX_START + 3, "c", {}),
            (UNIX_START + 1, "a", {}),
            (UNIX_START + 2, "b", {}),
        ]
        fake = _FakeLogAPI({(UNIX_START, UNIX_END): _loki_response(entries)})

        result, _ = _invoke(_base_args(), fake)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(len(fake.unit_calls()), 1)
        self.assertEqual(fake.unit_calls()[0]["direction"], "forward")
        # Chronological order regardless of Loki response order.
        idx_a = result.output.index('"a"')
        idx_b = result.output.index('"b"')
        idx_c = result.output.index('"c"')
        self.assertTrue(idx_a < idx_b < idx_c)
        self.assertIn("👆Time range: UTC|", result.output)
        self.assertIn("total 3 lines", result.output)

    def test_nonempty_fetch_makes_exactly_one_http_call(self):
        """A nonempty, non-saturating adaptive fetch makes exactly one HTTP
        request total: the root unit's own fetch.
        """
        fake = _FakeLogAPI(
            {(UNIX_START, UNIX_END): _loki_response([(UNIX_START + 1, "a", {})])}
        )

        result, _ = _invoke(_base_args(), fake)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(len(fake.calls), 1)


# ---------------------------------------------------------------------------
# empty interval
# ---------------------------------------------------------------------------


class TestEmptyInterval(unittest.TestCase):
    def test_empty_result_prints_no_logs_found_and_exits_zero(self):
        """The adaptive (no-`--limit`) path dispatches straight into the
        scheduler: the scheduler's own root fetch for `[S, E)` resolves
        empty (zero entries, zero failed units), and `run()` prints "No logs
        found" instead of the normal zero-line summary.
        """
        S, E = UNIX_START, UNIX_END
        fake = _FakeLogAPI({(S, E): {"data": {"result": []}}})

        result, _ = _invoke(_base_args(), fake)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("No logs found in the specified time range.", result.output)
        self.assertNotIn("Total:", result.output)
        # Exactly one HTTP call: the root fetch. No separate probe request.
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(len(fake.unit_calls()), 1)

    def test_empty_result_with_path_leaves_no_file_on_disk(self):
        """`--path` naming an *already-existing* directory: `resolve_save_path`
        treats it as directory-mode (auto-generated filename inside it), a
        different resolution branch than a direct file path or a
        not-yet-existing directory. A genuinely empty, fully-successful
        adaptive run must still never create a file inside it, proving file
        opening is deferred independently of whether directory creation
        itself was needed.
        """
        S, E = UNIX_START, UNIX_END
        fake = _FakeLogAPI({(S, E): {"data": {"result": []}}})
        outdir = tempfile.mkdtemp(dir=tmpdir)

        result, _ = _invoke(_base_args("--path", outdir), fake)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("No logs found in the specified time range.", result.output)
        self.assertEqual(glob.glob(os.path.join(outdir, "*.txt")), [])

    def test_empty_result_with_path_targeting_nonexistent_directory_never_creates_it(
        self,
    ):
        """The stronger version of the test above: the target directory
        doesn't exist at all yet. A genuinely empty adaptive result must
        never create it -- proving path resolution (which creates the
        directory via `os.makedirs`) is deferred, not just file opening.
        """
        S, E = UNIX_START, UNIX_END
        fake = _FakeLogAPI({(S, E): {"data": {"result": []}}})
        outdir = os.path.join(tmpdir, "never-created-empty-run-dir")
        self.assertFalse(os.path.exists(outdir))

        result, _ = _invoke(_base_args("--path", outdir), fake)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("No logs found in the specified time range.", result.output)
        self.assertFalse(
            os.path.exists(outdir),
            "an empty adaptive result must never create the --path directory",
        )

    def test_empty_result_with_path_targeting_existing_file_preserves_content(self):
        """Critical data-preservation test: `--path` naming an existing file
        with real prior content. Since path resolution and file opening are
        deferred to the first actual write need, a genuinely empty result
        never opens (and thus never truncates) a pre-existing file at all.
        """
        S, E = UNIX_START, UNIX_END
        fake = _FakeLogAPI({(S, E): {"data": {"result": []}}})
        outpath = os.path.join(tempfile.mkdtemp(dir=tmpdir), "pre-existing.txt")
        original_content = "these are pre-existing, precious log lines\n" * 3
        with open(outpath, "w", encoding="utf-8") as f:
            f.write(original_content)

        result, _ = _invoke(_base_args("--path", outpath), fake)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("No logs found in the specified time range.", result.output)
        with open(outpath, encoding="utf-8") as f:
            self.assertEqual(
                f.read(),
                original_content,
                "a pre-existing file at --path must be byte-for-byte"
                " unchanged after an empty adaptive result",
            )


# ---------------------------------------------------------------------------
# API failures and retries
# ---------------------------------------------------------------------------


class TestApiFailuresAndRetries(unittest.TestCase):
    """Proves the CLI's own human-readable warning text (naming the failed
    range and "missing from the output") on a partial-result exit."""

    def test_permanent_failure_on_one_unit_surfaces_as_warning_exit_2(self):
        S, E = UNIX_START, UNIX_END
        T = S + 1_000_000  # < branch_mid -> two children
        split_mid = T + (E - T) // 2
        page = _pad_entries(10000, S, T, "p")
        fake = _FakeLogAPI({
            (S, E): _loki_response(page),
            (T, split_mid): RuntimeError("permanent"),
            (split_mid, E): _loki_response([(split_mid + 5, "ok-sibling", {})]),
        })

        with patch.object(log_mod, "_interruptible_sleep", return_value=None):
            result, _ = _invoke(_base_args(), fake)

        self.assertEqual(result.exit_code, 2, result.output)
        # The permanently-failing unit was retried the full budget.
        failing_calls = [
            c for c in fake.unit_calls() if (c["start"], c["end"]) == (T, split_mid)
        ]
        self.assertEqual(len(failing_calls), 5)
        # Sibling data is still emitted.
        self.assertIn('"ok-sibling"', result.output)
        # A warning names the failed range. Normalize whitespace first since
        # the rich console line-wraps long sentences.
        normalized = " ".join(result.output.split())
        self.assertIn("could not be fetched after 5 retries", normalized)
        self.assertIn("missing from the output", normalized)
        self.assertIn(_epoch_to_time_str(T), normalized)
        self.assertIn(_epoch_to_time_str(split_mid), normalized)
        # It's still a real summary, not a claim of full success.
        self.assertIn("👆Time range: UTC|", normalized)


# ---------------------------------------------------------------------------
# worker concurrency
# ---------------------------------------------------------------------------


class TestWorkerConcurrency(unittest.TestCase):
    def test_workers_1_never_exceeds_one_in_flight(self):
        script = _build_tree_script()
        tracker = _InFlightTracker()
        fake = _FakeLogAPI(script, delay_fn=lambda key: 0.005, inflight=tracker)

        result, _ = _invoke(
            _base_args("--workers", "1", start=TREE_START_STR, end=TREE_END_STR),
            fake,
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(len(fake.unit_calls()), 5)
        self.assertLessEqual(tracker.max_seen, 1)

    def test_default_workers_is_32(self):
        fake = _FakeLogAPI(
            {(UNIX_START, UNIX_END): _loki_response([(UNIX_START + 1, "a", {})])}
        )
        captured = {}
        real_executor_cls = log_mod.ThreadPoolExecutor

        def spy_executor(*args, **kwargs):
            captured.update(kwargs)
            return real_executor_cls(*args, **kwargs)

        with patch.object(log_mod, "ThreadPoolExecutor", new=spy_executor):
            result, _ = _invoke(_base_args(), fake)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(captured.get("max_workers"), 32)


# ---------------------------------------------------------------------------
# --path output format + progress bar contrast
# ---------------------------------------------------------------------------


class TestPathOutputAndProgressBar(unittest.TestCase):
    def test_path_output_file_content_matches_format_exactly(self):
        S, E = UNIX_START, UNIX_END
        entries = [(S + 1, "hello", {}), (S + 2, "world", {})]
        fake = _FakeLogAPI({(S, E): _loki_response(entries)})
        outdir = tempfile.mkdtemp(dir=tmpdir)

        real_progress_cls = log_mod.Progress
        progress_calls = []

        def spy_progress(*args, **kwargs):
            progress_calls.append((args, kwargs))
            return real_progress_cls(*args, **kwargs)

        with patch.object(log_mod, "Progress", new=spy_progress):
            result, _ = _invoke(_base_args("--path", outdir), fake)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertTrue(progress_calls, "Progress must be instantiated for --path")

        files = glob.glob(os.path.join(outdir, "*.txt"))
        self.assertEqual(len(files), 1)
        with open(files[0], encoding="utf-8") as f:
            content = f.read()
        lines = content.splitlines(keepends=True)
        self.assertEqual(len(lines), 3)
        # File sink writes safe_load_json(line) directly (no json.dumps),
        # unlike the stdout sink -- plain strings appear unquoted.
        self.assertRegex(
            lines[0],
            r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}\｜hello\n$",
        )
        self.assertRegex(
            lines[1],
            r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}\｜world\n$",
        )
        self.assertRegex(
            lines[2],
            r"^Time range: UTC\|.+ → UTC\|.+ \| total 2 lines \n$",
        )
        self.assertIn("Successfully saved the log to:", result.output)


# ---------------------------------------------------------------------------
# LEGACY --limit path regression
# ---------------------------------------------------------------------------


class TestLegacyLimitPathRegression(unittest.TestCase):
    def test_limit_never_triggers_adaptive_helpers(self):
        S, E = UNIX_START, UNIX_END
        fake = _FakeLogAPI({})

        def _boom(*args, **kwargs):
            raise AssertionError("adaptive path must not run when --limit is set")

        with (
            patch.object(
                log_mod, "fetch_logs_adaptive_parallel", side_effect=_boom
            ) as adaptive_mock,
            patch.object(log_mod, "_fetch_log_unit", side_effect=_boom) as unit_mock,
        ):
            # Fake client needs to answer the LEGACY main call too.
            fake.script[(S, E)] = _loki_response(
                [(S + i, f"l{i}", {}) for i in range(5)]
            )
            result, _ = _invoke(_base_args("--limit", "5"), fake)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertFalse(adaptive_mock.called)
        self.assertFalse(unit_mock.called)

        # Independent signal: no call in this invocation ever used
        # direction="forward"; all rely on the backward default.
        for call in fake.calls:
            self.assertNotEqual(call.get("direction"), "forward")

        # LEGACY-specific summary text, byte-for-byte the same format as
        # today.
        self.assertIn("Time range: UTC|", result.output)
        self.assertIn("total 5 lines", result.output)

    def test_limit_with_path_never_triggers_adaptive_helpers(self):
        S, E = UNIX_START, UNIX_END
        fake = _FakeLogAPI(
            {(S, E): _loki_response([(S + i, f"l{i}", {}) for i in range(3)])}
        )
        outdir = tempfile.mkdtemp(dir=tmpdir)
        outpath = os.path.join(outdir, "legacy-out.txt")

        def _boom(*args, **kwargs):
            raise AssertionError("adaptive path must not run when --limit is set")

        with patch.object(
            log_mod, "fetch_logs_adaptive_parallel", side_effect=_boom
        ) as adaptive_mock:
            result, _ = _invoke(_base_args("--limit", "3", "--path", outpath), fake)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertFalse(adaptive_mock.called)
        for call in fake.calls:
            self.assertNotEqual(call.get("direction"), "forward")
        self.assertIn("Successfully saved the log to:", result.output)
        with open(outpath, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Time range: UTC|", content)
        self.assertIn("total 3 lines", content)

    def test_repl_path_never_triggers_adaptive_helpers(self):
        """REPL-path variant: `fetch_and_print_logs`/the REPL loop are
        closures nested inside `log_command`, not module-level symbols, so
        they cannot be unit-invoked directly; instead we drive them through
        a real (non-standalone) CLI invocation with stdin faked to report
        as an interactive tty, matching how the deprecated interactive
        prompt actually gates itself (`while True and sys.stdin.isatty()`).
        """
        S, E = UNIX_START, UNIX_END
        fake = _FakeLogAPI(
            {(S, E): _loki_response([(S + i, f"l{i}", {}) for i in range(5)])}
        )

        def _boom(*args, **kwargs):
            raise AssertionError("adaptive path must not run when --limit is set")

        client_cls = _make_client_class(fake)
        runner = CliRunner()
        with (
            patch.object(log_mod, "APIClient", client_cls),
            patch.object(
                log_mod, "fetch_logs_adaptive_parallel", side_effect=_boom
            ) as adaptive_mock,
            patch.object(cli_mod, "check_lepton_version", return_value=None),
        ):
            with runner.isolation(input="next 5\nquit\n") as outstreams:
                with patch("sys.stdin.isatty", return_value=True):
                    exc = None
                    try:
                        cli.main(
                            _base_args("--limit", "5"),
                            standalone_mode=False,
                        )
                    except SystemExit as e:
                        exc = e
                output = outstreams[0].getvalue().decode("utf-8", "replace")

        self.assertIsNone(exc, f"unexpected SystemExit: {exc}")
        self.assertFalse(adaptive_mock.called)
        self.assertIn("Enter a command", output)
        self.assertIn("Exiting log viewer.", output)
        for call in fake.calls:
            self.assertNotEqual(call.get("direction"), "forward")


# ---------------------------------------------------------------------------
# LogAPI.get_log rejects start=0/end=0 (end-to-end)
# ---------------------------------------------------------------------------


class TestInvalidAdaptiveBoundsRejectedFastCli(unittest.TestCase):
    """The adaptive (no-`--limit`) path must reject a non-positive
    `start`/`end` immediately at the CLI boundary, before ever dispatching a
    request -- not by letting the root work unit run the full
    retry-then-mark-failed gauntlet (5 attempts, real exponential backoff up
    to ~15s total) only to discover the precondition violation the slow way
    and report it as a generic partial failure (exit code 2).
    """

    def test_invalid_bounds_rejected_with_zero_dispatch(self):
        epoch_zero_start = "1970-01-01 00:00:00.000000"
        epoch_end = "1970-01-01 00:00:01.000000"
        self.assertEqual(_preprocess_time(epoch_zero_start, epoch=True), 0)

        cases = {
            "zero_start": _base_args(start=epoch_zero_start, end=epoch_end),
            # end=0 is only reachable past the pre-existing `end <= start`
            # inverted-range check (which fires first) when start is itself
            # negative -- so this necessarily also exercises a negative start.
            "zero_end": _base_args(start="-1000", end="0"),
            "negative_start": _base_args(start="-5", end="1000000000"),
        }

        for name, args in cases.items():
            with self.subTest(name):
                fake = _FakeLogAPI({})
                result, _ = _invoke(args, fake)

                self.assertEqual(result.exit_code, 1, result.output)
                self.assertEqual(fake.calls, [], "no request should ever be dispatched")
                self.assertNotIn("Traceback", result.output)


class TestEndAfterStartAndNegativeTimestampEndToEndCli(unittest.TestCase):
    """Drives `lep log get` through the full CLI, proving `end <= start` is
    rejected end-to-end and not an unhandled traceback. The negative/zero
    `start`/`end` cases (previously here too) now have their own dedicated
    fast-fail coverage in `TestInvalidAdaptiveBoundsRejectedFastCli` above.
    """

    def test_end_before_start_is_rejected_with_clear_error(self):
        # Both non-zero, non-negative, but inverted. `fetch_log`'s own
        # `unix_end <= unix_start` guard is the first thing to catch this.
        later = "2024-01-01 00:00:02.000000"
        earlier = "2024-01-01 00:00:01.000000"

        real_log_api = LogAPI(_RealLogAPIHTTPClient())
        result, _ = _invoke(_base_args(start=later, end=earlier), real_log_api)

        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("End time must be greater than start time", result.output)
        self.assertNotIn("Traceback", result.output)

    def test_ordinary_ascending_range_is_not_rejected(self):
        """Control case: a legitimate range must not trip either new check."""
        fake = _FakeLogAPI(
            {(UNIX_START, UNIX_END): _loki_response([(UNIX_START + 1, "a", {})])}
        )
        result, _ = _invoke(_base_args(), fake)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("Failed to query logs", result.output)


# ---------------------------------------------------------------------------
# no success-implying text on a partial result, either mode
# ---------------------------------------------------------------------------


class TestPartialResultNoSuccessText(unittest.TestCase):
    """When `failed_units` is non-empty (and there is no sink failure),
    `--path` mode may not print any success-implying leading text and must
    instead print the "Partial result" wording in both the console output
    and the saved file's own footer."""

    def _fixture(self, fail):
        S, E = UNIX_START, UNIX_END
        T = S + 1_000_000  # < branch_mid -> two children
        split_mid = T + (E - T) // 2
        page = _pad_entries(10000, S, T, "p")
        script = {
            (S, E): _loki_response(page),
            (split_mid, E): _loki_response([(split_mid + 5, "ok-sibling", {})]),
        }
        script[(T, split_mid)] = (
            RuntimeError("permanent")
            if fail
            else _loki_response([(T + 5, "child-ok", {})])
        )
        return _FakeLogAPI(script)

    def test_path_mode_partial_result_suppresses_success_text(self):
        fake = self._fixture(fail=True)
        outdir = tempfile.mkdtemp(dir=tmpdir)

        with patch.object(log_mod, "_interruptible_sleep", return_value=None):
            result, _ = _invoke(_base_args("--path", outdir), fake)

        self.assertEqual(result.exit_code, 2, result.output)
        self.assertNotIn("Successfully saved the log to:", result.output)
        self.assertIn("Partial result", result.output)
        self.assertIn("saved incomplete log to:", result.output)
        normalized = " ".join(result.output.split())
        self.assertIn("could not be fetched after 5 retries", normalized)
        self.assertIn("Total:", result.output)

        files = glob.glob(os.path.join(outdir, "*.txt"))
        self.assertEqual(len(files), 1)
        with open(files[0], encoding="utf-8") as f:
            content = f.read()
        # The footer/file content itself never claims success either. The
        # file sink writes the line unquoted (no json.dumps), unlike stdout.
        self.assertNotIn("Successfully saved the log to:", content)
        self.assertIn("ok-sibling", content)
        # The partial marker is additive across both the console output and
        # the saved file's own footer in this single real run -- not a
        # replacement for the console gating asserted above.
        self.assertIn("PARTIAL RESULT:", content)
        self.assertIn(
            "time range(s) could not be fetched and are missing from this file:",
            content,
        )


if __name__ == "__main__":
    unittest.main()
