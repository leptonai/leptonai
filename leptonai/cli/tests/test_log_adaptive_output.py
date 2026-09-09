"""Unit tests for adaptive log-fetch output/sink lifecycle: stdout vs
`--path` formatting, progress-bar gating, the "Partial result"/"Successfully
saved" text contract, the lazy (deferred-open) file sink's footer/close
behavior, and broken-pipe handling.

Scheduler-owned state (pending/active/buffer, watermark, split, admission)
lives in `test_log_adaptive_scheduler.py`; single-request parsing/retry
lives in `test_log_adaptive_worker.py`. This file retains no
`_AdaptiveLogScheduler`-driven test beyond what's needed to exercise output
formatting -- the sole scheduler-level test proving a sink failure cancels
future submissions stays in `test_log_adaptive_scheduler.py`
(`TestAdaptiveSchedulerSinkFailure`).
"""

import builtins
import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai, matching
# the existing CLI test suite convention (test_job_cli.py).
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import heapq
import io
import unittest
from unittest.mock import patch

from loguru import logger

from leptonai.cli import log as log_mod
from leptonai.cli.log import (
    WorkUnit,
    _AdaptiveLogScheduler,
    _epoch_to_time_str,
    _FAILED_RANGES_FILE_CAP,
    fetch_logs_adaptive_parallel,
)
from leptonai.cli.tests._log_test_helpers import (
    RecordingFakeLogAPI as _RecordingFakeLogAPI,
    loki_response as _loki_response,
    make_client_class as _make_client_class,
)

# Captured before any test patches `builtins.open` -- `ConfigurableFakeFile`
# wraps a genuine file underneath a patched `open`, so it cannot call the
# (patched) name `open` itself.
_REAL_OPEN = open


class ConfigurableFakeFile:
    """Recording/flaky file-handle double for output-lifecycle tests. Wraps
    a real file, optionally injecting a write or close failure.

    `fail_write_at`: 1-indexed write() call at which (and after which)
    `fail_write_exc` is raised instead of writing.
    `fail_write_exc`: exception raised by a failing write(); defaults to
    `OSError("disk full")`.
    `fail_on_close`: if True, close() still closes the underlying file (so
    prior content is flushed) but then raises OSError.
    """

    def __init__(
        self,
        path,
        mode,
        encoding,
        fail_write_at=None,
        fail_write_exc=None,
        fail_on_close=False,
    ):
        self._f = _REAL_OPEN(path, mode, encoding=encoding)
        self._fail_write_at = fail_write_at
        self._fail_write_exc = fail_write_exc or OSError("disk full")
        self._fail_on_close = fail_on_close
        self.write_calls = 0
        self.close_calls = 0

    def write(self, data):
        self.write_calls += 1
        if self._fail_write_at is not None and self.write_calls >= self._fail_write_at:
            raise self._fail_write_exc
        return self._f.write(data)

    def close(self):
        self.close_calls += 1
        self._f.close()
        if self._fail_on_close:
            raise OSError("close failed")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def make_configurable_fake_open(**kwargs):
    """`builtins.open`-shaped side_effect constructing a
    `ConfigurableFakeFile` with the given failure config for every call.
    Returns (fake_open, instances) -- `instances` records every handle
    constructed, for assertions on write_calls/close_calls."""
    instances = []

    def fake_open(path, mode="r", encoding=None):
        f = ConfigurableFakeFile(path, mode, encoding, **kwargs)
        instances.append(f)
        return f

    return fake_open, instances


class TestSinkFailureOutputMessages(unittest.TestCase):
    """Output-message content/formatting for sink-cancellation failures --
    the sole scheduler-level test proving cancellation itself (an
    already-in-flight request bounding shutdown) lives in
    test_log_adaptive_scheduler.py's TestAdaptiveSchedulerSinkFailure.
    """

    def test_stdout_sink_failure_cancels_and_propagates_without_further_calls(self):
        # unit=[0, 20000); saturates into a single unsplit child covering
        # [14999, 20000). The parent's own sub-T entries are drained/emitted
        # right after the parent's future resolves -- before the child is
        # ever submitted -- so a sink failure on that first emit call must
        # prevent the child's request from ever being made.
        first_page = [(t, f"l{t}", {}) for t in range(5000, 15000)]
        fake = _RecordingFakeLogAPI({
            (0, 20000): _loki_response(first_page),
            (14999, 20000): _loki_response([(15500, "tail", {})]),
        })

        # A genuinely, permanently broken pipe fails on every write, not
        # just the first -- this is also what makes the BrokenPipeError
        # propagation path deterministic to test.
        def flaky_print(*args, **kwargs):
            raise BrokenPipeError("broken pipe")

        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.console, "print", side_effect=flaky_print),
            self.assertRaises(BrokenPipeError),
        ):
            fetch_logs_adaptive_parallel(
                None, "job-1", None, None, "", 0, 20000, 4, True, None
            )

        # Only the parent's fetch happened; cancellation must have prevented
        # the child unit from ever being submitted.
        requested_ranges = {(c["start"], c["end"]) for c in fake.calls}
        self.assertEqual(requested_ranges, {(0, 20000)})

    def test_lazy_open_failure_mid_stream_cancels_and_prevents_further_submission(self):
        """A lazy `--path` open failure surfacing mid-loop (via `emit()`,
        while a worker's fetch is genuinely in flight) is reported through
        the single generic sink-failure message, and must still cancel and
        prevent the child unit produced by the parent's saturation from ever
        being submitted.
        """
        first_page = [(t, f"l{t}", {}) for t in range(5000, 15000)]
        fake = _RecordingFakeLogAPI({
            (0, 20000): _loki_response(first_page),
            (14999, 20000): _loki_response([(15500, "tail", {})]),
        })
        outpath = os.path.join(tmpdir, "midloop_open_fail_out.txt")
        printed = []

        def fake_print(*args, **kwargs):
            printed.append(str(args[0]) if args else "")

        def fake_open(path, mode="r", encoding=None):
            raise OSError("disk full")

        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.console, "print", side_effect=fake_print),
            patch("builtins.open", side_effect=fake_open),
            self.assertRaises(SystemExit) as cm,
        ):
            fetch_logs_adaptive_parallel(
                None, "job-1", None, None, "", 0, 20000, 4, True, outpath
            )

        self.assertEqual(cm.exception.code, 1)
        requested_ranges = {(c["start"], c["end"]) for c in fake.calls}
        self.assertEqual(requested_ranges, {(0, 20000)})
        output = "\n".join(printed)
        self.assertIn("Failed to write logs", output)
        self.assertIn("disk full", output)
        self.assertNotIn("Successfully saved", output)
        self.assertNotIn("Partial result", output)

    def test_path_sink_broken_pipe_write_cancels_and_propagates_without_further_calls(
        self,
    ):
        """Verifies BrokenPipeError propagation, cancellation, and that the
        --path sink's file handle is closed."""
        first_page = [(t, f"l{t}", {}) for t in range(5000, 15000)]
        fake = _RecordingFakeLogAPI({
            (0, 20000): _loki_response(first_page),
            (14999, 20000): _loki_response([(15500, "tail", {})]),
        })
        outpath = os.path.join(tmpdir, "path_sink_broken_pipe_out.txt")
        fake_open, instances = make_configurable_fake_open(
            fail_write_at=1, fail_write_exc=BrokenPipeError("broken pipe")
        )

        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch("builtins.open", side_effect=fake_open),
            self.assertRaises(BrokenPipeError),
        ):
            fetch_logs_adaptive_parallel(
                None, "job-1", None, None, "", 0, 20000, 4, True, outpath
            )

        requested_ranges = {(c["start"], c["end"]) for c in fake.calls}
        self.assertEqual(requested_ranges, {(0, 20000)})
        self.assertEqual(instances[0].close_calls, 1)

    def test_lazy_open_failure_at_zero_entry_partial_finalization_exits_1(self):
        """A zero-entry partial run (no entries ever emitted, but nonzero
        `failed_units`) still reaches the footer-write finalization step,
        which triggers the lazy open. If that open fails, `run()` must exit
        1 before printing any summary/success text.
        """
        outpath = os.path.join(
            tempfile.mkdtemp(dir=tmpdir), "finalization_open_fail.txt"
        )

        def fake_open(path, mode="r", encoding=None):
            raise OSError("disk full")

        sched = _AdaptiveLogScheduler(
            None, "job-1", None, None, "", 0, 100, 4, True, outpath
        )
        sched.pending = []
        # No entries were ever emitted, but nonzero `failed_units` still
        # forces `run()` to reach the footer-write finalization step.
        sched.failed_units = [(0, 100)]

        printed = []

        def fake_print(*args, **kwargs):
            printed.append(str(args[0]) if args else "")

        with (
            patch.object(log_mod.console, "print", side_effect=fake_print),
            patch("builtins.open", side_effect=fake_open),
            self.assertRaises(SystemExit) as cm,
        ):
            sched.run()

        self.assertEqual(cm.exception.code, 1)
        output = "\n".join(printed)
        self.assertIn("Failed to write logs", output)
        self.assertIn("disk full", output)
        self.assertNotIn("Successfully saved", output)
        self.assertNotIn("Partial result", output)
        self.assertNotIn("Time range:", output)


class TestProgressBarAndSummaryFormat(unittest.TestCase):
    """`Progress()` is instantiated inside `_AdaptiveLogScheduler.run()`
    itself (gated on whether `path` is set), not CLI/Click glue, so these
    tests don't need the CLI layer. The one full end-to-end `--path` output
    case (file content/format) lives in test_log_cli.py's
    TestPathOutputAndProgressBar per the compact CLI-integration matrix.
    """

    def test_no_progress_bar_for_stdout_output(self):
        fake = _RecordingFakeLogAPI({(0, 100): _loki_response([(1, "a", {})])})
        progress_calls = []
        real_progress_cls = log_mod.Progress

        def spy_progress(*args, **kwargs):
            progress_calls.append((args, kwargs))
            return real_progress_cls(*args, **kwargs)

        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod, "Progress", new=spy_progress),
            self.assertRaises(SystemExit) as cm,
        ):
            fetch_logs_adaptive_parallel(
                None, "job-1", None, None, "", 0, 100, 4, True, None
            )

        self.assertEqual(cm.exception.code, 0)
        self.assertFalse(
            progress_calls, "Progress must NOT be instantiated for stdout output"
        )

    def test_stdout_summary_uses_one_line_emoji_format(self):
        """Stdout mode's final summary must print the original one-line
        `👆Time range: UTC|... → UTC|... total N lines` format, NOT the
        multi-line `Time range:` / `Total:` / `Duration:` console block that
        `--path` mode prints (that block remains `--path`-only). Redirects
        the real `console`'s output file to a buffer (rather than capturing
        raw `print()` call args) so markup is actually rendered to plain
        text, the same way `CliRunner` renders it for a real terminal-less
        run.
        """
        fake = _RecordingFakeLogAPI({(0, 100): _loki_response([(1, "hello", {})])})
        buf = io.StringIO()
        # `Console.file` is a property that, when the internal `_file` is
        # None, dynamically resolves to the *current* `sys.stdout` on every
        # access -- which is how `CliRunner` transparently captures rich
        # output in other tests. Saving/restoring via the `.file` property
        # itself would instead snapshot a *fixed* stdout reference into
        # `_file`, permanently breaking that dynamic resolution for every
        # later test in the process that relies on it (leaking across test
        # files). Save/restore the private `_file` attribute directly so
        # this redirection is fully undone afterward.
        real_file = log_mod.console._file
        log_mod.console.file = buf
        try:
            with (
                patch.object(log_mod, "APIClient", _make_client_class(fake)),
                self.assertRaises(SystemExit) as cm,
            ):
                fetch_logs_adaptive_parallel(
                    None, "job-1", None, None, "", 0, 100, 4, True, None
                )
        finally:
            log_mod.console._file = real_file

        self.assertEqual(cm.exception.code, 0)
        output = buf.getvalue()
        self.assertIn("👆Time range: UTC|", output)
        self.assertIn("total 1 lines", output)
        self.assertNotIn("Total:", output)
        self.assertNotIn("Duration:", output)
        self.assertNotIn("Successfully saved", output)


class TestNoSuccessTextOnPartialFailure(unittest.TestCase):
    """When `failed_units` is non-empty (and there was no
    sink failure), neither mode may print any success-implying leading text;
    both must print the "Partial result" replacement instead.
    """

    def _run(self, path):
        S, E = 0, 10000
        T = 1_000  # < branch_mid=5000 -> two children
        split_mid = T + (E - T) // 2
        # 10000 entries cycling within [0, T] so the page saturates with
        # max_ts == T (rather than the full [S, E) range).
        page = [(i % (T + 1), f"l{i}", {}) for i in range(9999)]
        page.append((T, "l-max", {}))
        self.assertEqual(len(page), 10000)
        fake = _RecordingFakeLogAPI({
            (S, E): _loki_response(page),
            (T, split_mid): RuntimeError("permanent"),
            (split_mid, E): _loki_response([(split_mid + 5, "ok-sibling", {})]),
        })
        printed = []

        def fake_print(*args, **kwargs):
            printed.append(str(args[0]) if args else "")

        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod, "_interruptible_sleep", return_value=None),
            patch.object(log_mod.console, "print", side_effect=fake_print),
            self.assertRaises(SystemExit) as cm,
        ):
            fetch_logs_adaptive_parallel(
                None, "job-1", None, None, "", S, E, 4, True, path
            )
        self.assertEqual(cm.exception.code, 2)
        return "\n".join(printed)

    def test_path_mode_no_success_text_prints_partial_result(self):
        outpath = os.path.join(tmpdir, "no_success_text_path_out.txt")
        output = self._run(outpath)
        self.assertNotIn("Successfully saved", output)
        self.assertIn("Partial result", output)
        self.assertIn(f"saved incomplete log to: {outpath}", output)

    def test_stdout_mode_no_success_text_prints_partial_result(self):
        output = self._run(None)
        self.assertNotIn("Successfully saved", output)
        self.assertIn("Partial result", output)
        self.assertIn("log output is incomplete", output)

    def _run_success(self, path):
        """Same shape as `_run` above, but nothing fails -- proving the
        gating above is bidirectional, not just a one-way "always show
        partial" bug.
        """
        S, E = 0, 10000
        T = 1_000
        split_mid = T + (E - T) // 2
        page = [(i % (T + 1), f"l{i}", {}) for i in range(9999)]
        page.append((T, "l-max", {}))
        fake = _RecordingFakeLogAPI({
            (S, E): _loki_response(page),
            (T, split_mid): _loki_response([(T + 5, "child-ok", {})]),
            (split_mid, E): _loki_response([(split_mid + 5, "ok-sibling", {})]),
        })
        printed = []

        def fake_print(*args, **kwargs):
            printed.append(str(args[0]) if args else "")

        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod.console, "print", side_effect=fake_print),
            self.assertRaises(SystemExit) as cm,
        ):
            fetch_logs_adaptive_parallel(
                None, "job-1", None, None, "", S, E, 4, True, path
            )
        self.assertEqual(cm.exception.code, 0)
        return "\n".join(printed)

    def test_control_no_failure_bidirectional_gating(self):
        path_output = self._run_success(
            os.path.join(tmpdir, "no_success_text_control_path_out.txt")
        )
        self.assertIn("Successfully saved", path_output)
        self.assertNotIn("Partial result", path_output)

        stdout_output = self._run_success(None)
        self.assertNotIn("Partial result", stdout_output)
        self.assertNotIn("Successfully saved", stdout_output)


class TestFileFooterPartialResultMarker(unittest.TestCase):
    """The saved `--path` file's footer states partial/incomplete when
    `failed_units` is non-empty, including a capped summary of failed
    ranges; the file footer is unchanged when nothing failed.

    Each test constructs an `_AdaptiveLogScheduler` with an empty `pending`
    queue (so `run()`'s fetch loop does nothing) and manually seeds
    `failed_units`, isolating the file-footer-writing behavior from
    bisection/scheduling mechanics (already covered elsewhere in this file).
    """

    def _run_with_failed_units(self, failed_units):
        path = os.path.join(tempfile.mkdtemp(dir=tmpdir), "out.txt")
        sched = _AdaptiveLogScheduler(
            None, "job-1", None, None, "", 0, 100, 4, True, path
        )
        sched.pending = []
        sched.failed_units = list(failed_units)
        # A genuinely empty run (0 lines, 0 failures) short-circuits via the
        # "No logs found" branch, which never creates the output file at all
        # -- seed a nonzero line count so the "empty -- footer unchanged"
        # case still exercises (and this test can still read) the normal
        # footer-write path being tested here.
        sched.bookkeeping.total_lines = 1

        records = []
        handler_id = logger.add(
            lambda msg: records.append(msg.record["message"]), level="TRACE"
        )
        try:
            with self.assertRaises(SystemExit) as cm:
                sched.run()
        finally:
            logger.remove(handler_id)

        with open(path, encoding="utf-8") as f:
            content = f.read()
        return cm.exception.code, content, records

    def test_footer_cap_boundary_cases(self):
        """Table-driven: the failed-units-count-vs-`_FAILED_RANGES_FILE_CAP`
        boundary. All 5 cases share the exact same mechanism
        (`_run_with_failed_units` + footer cap truncation), varying only the
        failed-units count relative to the cap (zero, under, exactly-at,
        one-over, exceeding); each still asserts exit code, footer line
        count/text, and (for the truncating cases) that the full untruncated
        list reaches the trace log while the file itself stays truncated.

        Widely-spaced (10s apart) ranges are used whenever count > 1 so each
        range formats to a distinct, non-overlapping display string --
        microsecond-resolution formatting would otherwise collapse
        tightly-packed ns timestamps.
        """
        step = 10_000_000_000
        cap = _FAILED_RANGES_FILE_CAP

        def _ranges(n):
            return [(i * step, i * step + 5_000_000) for i in range(n)]

        cases = [
            ("empty -- footer unchanged", _ranges(0), None),
            ("small, under cap -- uncapped", [(10, 20), (30, 40)], None),
            ("exactly at cap -- not truncated", _ranges(cap), None),
            ("one over cap -- '+1 more'", _ranges(cap + 1), 1),
            ("exceeding cap -- '+N more'", _ranges(cap + 3), 3),
        ]

        for description, failed_units, remaining in cases:
            with self.subTest(description=description):
                exit_code, content, records = self._run_with_failed_units(failed_units)
                lines = content.splitlines()

                if not failed_units:
                    self.assertEqual(exit_code, 0)
                    self.assertEqual(len(lines), 1)
                    self.assertTrue(lines[0].startswith("Time range: UTC|"))
                    self.assertNotIn("PARTIAL RESULT", content)
                    continue

                self.assertEqual(exit_code, 2)
                self.assertEqual(len(lines), 2)
                self.assertTrue(lines[0].startswith("Time range: UTC|"))
                capped = failed_units[:cap]
                expected_ranges = ", ".join(
                    f"[{_epoch_to_time_str(s)}, {_epoch_to_time_str(e)})"
                    for s, e in capped
                )
                if remaining is None:
                    # Under or exactly-at the cap: no truncation suffix.
                    self.assertEqual(
                        lines[1],
                        f"PARTIAL RESULT: {len(failed_units)} time range(s) could"
                        " not be fetched and are missing from this file:"
                        f" {expected_ranges}",
                    )
                    self.assertNotIn("more, see trace log", content)
                else:
                    self.assertEqual(
                        lines[1],
                        f"PARTIAL RESULT: {len(failed_units)} time range(s) could"
                        " not be fetched and are missing from this file:"
                        f" {expected_ranges} (+{remaining} more,"
                        " see trace log for full list)",
                    )
                    # Full untruncated list only goes to the trace log,
                    # never the file.
                    full_list_traced = any(
                        all(str((s, e)) in r for s, e in failed_units) for r in records
                    )
                    self.assertTrue(full_list_traced)
                    for s, e in failed_units[cap:]:
                        self.assertNotIn(_epoch_to_time_str(s), content)


class TestPartialRunWithZeroEntriesCreatesFileLazily(unittest.TestCase):
    """A genuinely partial run -- its only unit fails permanently, so zero
    entries are ever emitted but `failed_units`
    ends up non-empty -- must still create the `--path` output file, with
    the partial-result footer, driven through a real `run()` (unlike
    `TestFileFooterPartialResultMarker` above, which manually seeds
    `bookkeeping.total_lines`/`failed_units` to isolate the footer-writing
    mechanics in isolation). This exercises the lazy sink's other deferred-
    open trigger: reaching finalization with nonempty `failed_units`, not an
    emitted entry.
    """

    def test_all_units_fail_still_creates_file_with_partial_footer(self):
        fake = _RecordingFakeLogAPI({(0, 100): RuntimeError("permanent")})
        outdir = tempfile.mkdtemp(dir=tmpdir)
        outpath = os.path.join(outdir, "all_failed_out.txt")

        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch.object(log_mod, "_interruptible_sleep", return_value=None),
            self.assertRaises(SystemExit) as cm,
        ):
            fetch_logs_adaptive_parallel(
                None, "job-1", None, None, "", 0, 100, 4, True, outpath
            )

        self.assertEqual(cm.exception.code, 2)
        self.assertTrue(
            os.path.exists(outpath),
            "the output file must be created for a partial run even when"
            " zero entries were ever emitted",
        )
        with open(outpath, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("total 0 lines", content)
        self.assertIn("PARTIAL RESULT:", content)
        self.assertIn(
            "time range(s) could not be fetched and are missing from this file:",
            content,
        )


class TestFooterViaOpenHandle(unittest.TestCase):
    """The saved `--path` file's footer is written through the same still-
    open `f` handle used for streaming entries -- no second `open(path, "a")`
    call -- and output-lifecycle failures at the open/footer-write/close
    steps are caught and reported via `console.print`, never left uncaught.
    """

    def _scheduler(self, path):
        sched = _AdaptiveLogScheduler(
            None, "job-1", None, None, "", 0, 100, 4, True, path
        )
        sched.pending = []  # isolate footer-writing behavior
        # A genuinely empty run (0 lines, 0 failures) short-circuits via the
        # "No logs found" branch before ever reaching the footer/close logic
        # under test here -- seed a nonzero line count so these tests keep
        # exercising the normal footer-write/close path.
        sched.bookkeeping.total_lines = 1
        return sched

    def test_only_one_open_call_no_reopen_for_footer(self):
        outdir = tempfile.mkdtemp(dir=tmpdir)
        outpath = os.path.join(outdir, "single_open.txt")
        sched = self._scheduler(outpath)

        real_open = builtins.open
        open_calls = []

        def counting_open(path, mode="r", encoding=None, *args, **kwargs):
            open_calls.append((path, mode))
            return real_open(path, mode, encoding=encoding, *args, **kwargs)

        with (
            patch("builtins.open", side_effect=counting_open),
            self.assertRaises(SystemExit) as cm,
        ):
            sched.run()

        self.assertEqual(cm.exception.code, 0)
        matching = [c for c in open_calls if c[0] == outpath]
        self.assertEqual(
            len(matching),
            1,
            f"expected exactly one open() call for {outpath}, got {matching}",
        )
        self.assertEqual(matching[0][1], "w")

    # A lazy-open failure at finalization time is covered by
    # TestSinkFailureOutputMessages
    # .test_lazy_open_failure_at_zero_entry_partial_finalization_exits_1.

    def test_footer_write_vs_close_failure(self):
        """Footer-write and close failures both print exactly one failure
        message and no success text, but differ in whether the footer ends
        up on disk (fail_write_at=1: no streaming writes precede the footer
        write, so it's the first write() call; a close failure instead
        happens strictly after a successful footer write)."""
        cases = {
            "footer_write_fails": {
                "open_kwargs": {"fail_write_at": 1},
                "expected_message": "Failed to write log file footer",
                "footer_on_disk": False,
            },
            "close_fails_after_footer_written": {
                "open_kwargs": {"fail_on_close": True},
                "expected_message": "Failed to close output file",
                "footer_on_disk": True,
            },
        }
        for name, case in cases.items():
            with self.subTest(name):
                outdir = tempfile.mkdtemp(dir=tmpdir)
                outpath = os.path.join(outdir, f"{name}.txt")
                sched = self._scheduler(outpath)
                fake_open, _ = make_configurable_fake_open(**case["open_kwargs"])
                printed = []

                def fake_print(*args, **kwargs):
                    printed.append(str(args[0]) if args else "")

                with (
                    patch("builtins.open", side_effect=fake_open),
                    patch.object(log_mod.console, "print", side_effect=fake_print),
                    self.assertRaises(SystemExit) as cm,
                ):
                    sched.run()

                self.assertEqual(cm.exception.code, 1)
                output = "\n".join(printed)
                self.assertIn(case["expected_message"], output)
                self.assertNotIn("Successfully saved", output)
                self.assertNotIn("Partial result", output)
                self.assertEqual(
                    sum(
                        output.count(msg)
                        for msg in (
                            "Failed to write log file footer",
                            "Failed to close output file",
                        )
                    ),
                    1,
                    "exactly one failure message must be printed",
                )
                with open(outpath, encoding="utf-8") as f:
                    content = f.read()
                self.assertEqual("Time range: UTC|" in content, case["footer_on_disk"])


class TestPostRetrievalPrintFailurePropagatesUncaught(unittest.TestCase):
    """Regression test for the removal of the old catch-and-translate
    console-print helper: a `console.print` failure (e.g. `BrokenPipeError`)
    at one of the
    post-retrieval "success-path" print sites -- the failed-units warning,
    the final rich summary block, and the success/partial-success lines --
    is no longer caught and translated into `sys.exit(1)`; it now propagates
    out of `run()` as a normal uncaught exception. The mid-stream/in-loop
    case (a `console.print` failure while a fetch is still genuinely in
    flight, which surfaces through the existing sink-failure machinery and
    still exits 1) is unrelated and stays covered by
    `TestSinkFailureOutputMessages` here and
    `TestAdaptiveSchedulerSinkFailure` in test_log_adaptive_scheduler.py.
    """

    def test_broken_pipe_on_no_logs_found_print_propagates_uncaught(self):
        # stdout mode (path=None), empty `pending` so `run()`'s fetch loop
        # does nothing, and the constructor-seeded defaults (total_lines=0,
        # failed_units=[]) drive straight into the zero-entry/no-failures
        # "No logs found" branch -- the simplest post-retrieval print site
        # to isolate, with only a single `console.print` call in play.
        sched = _AdaptiveLogScheduler(
            None, "job-1", None, None, "", 0, 100, 4, True, None
        )
        sched.pending = []

        def flaky_print(*args, **kwargs):
            raise BrokenPipeError("broken pipe")

        with (
            patch.object(log_mod.console, "print", side_effect=flaky_print),
            self.assertRaises(BrokenPipeError),
        ):
            sched.run()


class TestBestEffortCloseFlushesStreamedContent(unittest.TestCase):
    """On a `sink_exc`/`watermark_exc` early exit or a footer-write failure,
    a silent best-effort `f.close()` is attempted before `sys.exit(1)`: small
    writes must be explicitly closed to reach disk, so these tests prove
    already-streamed content isn't left stranded in the write buffer and
    lost. Each covers a distinct trigger (entry-write failure, watermark
    regression, footer-write failure), so they're kept as separate methods
    rather than one table.

    `assertRaises(SystemExit)` clears `run()`'s frame locals (including
    `f`) as a side effect of clearing the caught exception's traceback,
    which would incidentally flush `f` via its own implicit GC-driven close
    regardless of whether `run()`'s own explicit best-effort close exists.
    The entry-write-failure and watermark-regression tests below use a
    plain try/except to avoid that false pass; the footer-write-failure
    test's content is proven flushed independently by its own success (5
    real entries streamed, only the 6th write -- the footer -- fails), so
    it doesn't need the same workaround.
    """

    def test_entry_write_failure_preserves_streamed_content(self):
        # A single small, non-saturating unit resolves in one shot, so its
        # three entries are drained and emitted together in one batch, well
        # under the TextIOWrapper write buffer's several-KB auto-flush
        # threshold -- keeping content this small means the only way the
        # first two entries' writes can reach disk before sys.exit is the
        # best-effort explicit close on the sink_exc path, not an unrelated
        # buffer auto-flush.
        real_open = builtins.open
        fake = _RecordingFakeLogAPI({
            (0, 100): _loki_response([
                (1, "s1", {}),
                (2, "s2", {}),
                (3, "s3", {}),
            ]),
        })
        outpath = os.path.join(tmpdir, "sink_fail_flush_small_out.txt")
        fake_open, _ = make_configurable_fake_open(fail_write_at=3)

        exit_code = None
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch("builtins.open", side_effect=fake_open),
        ):
            try:
                fetch_logs_adaptive_parallel(
                    None, "job-1", None, None, "", 0, 100, 4, True, outpath
                )
            except SystemExit as exc:
                exit_code = exc.code

        self.assertEqual(exit_code, 1)
        with real_open(outpath, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("s1", content)
        self.assertIn("s2", content)

    def test_watermark_regression_preserves_streamed_content(self):
        # Two small units, `--workers 1` so they resolve strictly serially:
        # the first unit's two entries stream and its watermark advances
        # normally before `_compute_watermark` is forced to regress on the
        # second unit's call, injecting the watermark_exc failure only
        # after real content has streamed.
        real_open = builtins.open
        fake = _RecordingFakeLogAPI({
            (0, 10): _loki_response([(1, "wa1", {}), (2, "wa2", {})]),
            (10, 20): _loki_response([(11, "wb1", {})]),
        })
        outpath = os.path.join(tmpdir, "watermark_fail_flush_small_out.txt")
        fake_open, instances = make_configurable_fake_open()

        real_compute_watermark = log_mod._AdaptiveLogScheduler._compute_watermark
        call_state = {"n": 0}

        def fake_compute_watermark(self):
            call_state["n"] += 1
            if call_state["n"] == 1:
                return real_compute_watermark(self)
            return -1

        sched = _AdaptiveLogScheduler(
            None, "job-1", None, None, "", 0, 20, 1, True, outpath
        )
        sched.pending = []  # drop the constructor-seeded [0, 20) unit
        heapq.heappush(sched.pending, WorkUnit(sched._next_seq(), 0, 10))
        heapq.heappush(sched.pending, WorkUnit(sched._next_seq(), 10, 20))

        printed = []

        def fake_print(*args, **kwargs):
            printed.append(str(args[0]) if args else "")

        exit_code = None
        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch("builtins.open", side_effect=fake_open),
            patch.object(log_mod.console, "print", side_effect=fake_print),
            patch.object(
                log_mod._AdaptiveLogScheduler,
                "_compute_watermark",
                fake_compute_watermark,
            ),
        ):
            try:
                sched.run()
            except SystemExit as exc:
                exit_code = exc.code

        self.assertEqual(exit_code, 1)
        self.assertIn("Internal scheduling error", "\n".join(printed))
        # A best-effort close IS attempted on the watermark_exc path.
        self.assertEqual(instances[0].close_calls, 1)
        with real_open(outpath, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("wa1", content)
        self.assertIn("wa2", content)

    def test_footer_write_failure_preserves_streamed_content(self):
        # A single, non-saturating page: one fetch resolves the whole
        # range, all 5 entries stream successfully, and only afterward does
        # the footer write (the 6th write() call) fail.
        real_open = builtins.open
        first_page = [(t, f"l{t}", {}) for t in range(10, 15)]
        fake = _RecordingFakeLogAPI({(0, 100): _loki_response(first_page)})
        outpath = os.path.join(tmpdir, "footer_fail_flush_out.txt")
        fake_open, _ = make_configurable_fake_open(fail_write_at=6)

        printed = []

        def fake_print(*args, **kwargs):
            printed.append(str(args[0]) if args else "")

        with (
            patch.object(log_mod, "APIClient", _make_client_class(fake)),
            patch("builtins.open", side_effect=fake_open),
            patch.object(log_mod.console, "print", side_effect=fake_print),
            self.assertRaises(SystemExit) as cm,
        ):
            fetch_logs_adaptive_parallel(
                None, "job-1", None, None, "", 0, 100, 4, True, outpath
            )

        self.assertEqual(cm.exception.code, 1)
        with real_open(outpath, encoding="utf-8") as f:
            content = f.read()
        # The 5 already-streamed lines survive the best-effort close, even
        # though the footer itself is absent/incomplete.
        for t in range(10, 15):
            self.assertIn(f"l{t}", content)
        self.assertNotIn("Time range: UTC|", content)

        # Exactly one failure is reported -- the footer-write failure --
        # never a second close-failure message, since the best-effort close
        # on this path is silent even if it also fails.
        output = "\n".join(printed)
        self.assertIn("Failed to write log file footer", output)
        self.assertNotIn("Failed to close output file", output)
