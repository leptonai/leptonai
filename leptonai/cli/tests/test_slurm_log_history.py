"""Slurm history uses the same time-window retrieval as other workloads."""

import importlib
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from leptonai.cli import lep
from leptonai.cli.tests._log_test_helpers import loki_response
from leptonai.cli.tests.test_slurm_cli import JOBS, _fake_client


log_module = importlib.import_module("leptonai.cli.log")
START = 1_704_067_200_000_000_000
END = START + 30_000


@pytest.fixture
def history_client():
    client, api = _fake_client()
    client.log = Mock()
    client.log.get_log.return_value = loki_response([])
    # --id with --cluster resolves inside that cluster.
    api.list_cluster_jobs.return_value = [JOBS.jobs[0]]
    with (
        patch("leptonai.cli.slurm.APIClient", return_value=client),
        patch.object(log_module, "APIClient", return_value=client),
        patch("leptonai.cli.cli.check_lepton_version"),
    ):
        yield client, api


def _serve(client, entries):
    def query(**kwargs):
        selected = [
            entry for entry in entries if kwargs["start"] <= entry[0] < kwargs["end"]
        ]
        selected.sort(
            key=lambda entry: entry[0], reverse=kwargs.get("direction") == "backward"
        )
        return loki_response(selected[: kwargs["limit"]])

    client.log.get_log.side_effect = query


def _invoke(*args, selector=("--id", "42")):
    return CliRunner().invoke(lep, ["slurm", "job", "log", *selector, *args])


def _lines(result):
    return [
        line
        for line in result.output.splitlines()
        if line.startswith(("line-", "boundary"))
    ]


@pytest.mark.parametrize(
    "selector",
    [("--id", "42"), ("--name", "train"), ("--id", "42", "--cluster", "cluster-a")],
)
def test_history_fetches_the_whole_window_with_slurm_filters(history_client, selector):
    client, api = history_client
    entries = [(START + i, f"line-{i}", {}) for i in range(9999)]
    entries += [
        (START + 10_000, "line-boundary-a", {"node": "node-a"}),
        (START + 10_000, "line-boundary-b", {"node": "node-a"}),
    ]
    _serve(client, entries)
    result = _invoke(
        "--start",
        str(START),
        "--end",
        str(END),
        "--attempt",
        "0",
        "--step",
        "42.batch",
        "--node",
        "node-a",
        "--log-type",
        "stderr",
        "--query",
        "line",
        *(["--workers", "2"] if selector[0] == "--name" else []),
        selector=selector,
    )

    assert result.exit_code == 0, result.output
    assert _lines(result) == [line for _, line, _ in entries]
    api.get_logs.assert_not_called()
    calls = client.log.get_log.call_args_list
    assert len(calls) > 1
    for call in calls:
        assert call.kwargs["direction"] == "forward"
        assert call.kwargs["limit"] == 10_000
        assert call.kwargs["slurm_namespace"] == "ns"
        assert call.kwargs["slurm_cluster"] == "cluster-a"
        assert call.kwargs["slurm_job"] == "42"
        assert str(call.kwargs["slurm_attempt"]) == "0"
        assert call.kwargs["slurm_step"] == "42.batch"
        assert call.kwargs["slurm_node"] == "node-a"
        assert call.kwargs["slurm_log_type"] == "stderr.log"
        assert call.kwargs["q"] == "line"


@pytest.mark.parametrize("limit", [2, 10001])
def test_history_limit_selects_latest_lines_without_losing_boundary_duplicates(
    history_client, limit
):
    client, api = history_client
    entries = [(START + 1, "boundary", {})] * 2
    entries += [(START + i, f"line-{i}", {}) for i in range(2, 10001)]
    _serve(client, entries)
    with (
        patch.object(log_module.sys.stdin, "isatty", return_value=True),
        patch("builtins.input", side_effect=AssertionError("unexpected prompt")),
    ):
        result = _invoke(
            "--start", str(START), "--end", str(END), "--limit", str(limit)
        )

    assert result.exit_code == 0, result.output
    assert _lines(result) == [line for _, line, _ in entries[-limit:]]
    assert "Enter a command" not in result.output
    api.get_logs.assert_not_called()
    assert all(
        call.kwargs["direction"] == "backward"
        for call in client.log.get_log.call_args_list
    )


@pytest.mark.parametrize(
    "args, expected_start, expected_end",
    [
        ([], START, START + 12 * 3600 * 10**9),
        (["--end", str(END)], START, END),
        (["--start", str(START + 1)], START + 1, START + 12 * 3600 * 10**9),
    ],
)
def test_history_defaults_to_today_and_now(
    history_client, args, expected_start, expected_end
):
    client, api = history_client

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2024, 1, 1, 12, tzinfo=timezone.utc).astimezone(tz)

    with patch.object(log_module, "datetime", FixedDatetime):
        result = _invoke(*args)

    assert result.exit_code == 0, result.output
    client.log.get_log.assert_called_once()
    kwargs = client.log.get_log.call_args.kwargs
    assert (kwargs["start"], kwargs["end"]) == (expected_start, expected_end)
    assert kwargs["q"] == ""
    api.get_logs.assert_not_called()


@pytest.mark.parametrize("start, end", [("0", str(END)), (str(END), str(START))])
def test_history_rejects_invalid_window(history_client, start, end):
    client, api = history_client
    result = _invoke("--start", start, "--end", end)

    assert result.exit_code != 0
    client.log.get_log.assert_not_called()
    api.get_logs.assert_not_called()


@pytest.mark.parametrize("args", [[], ["--limit", "2"]])
def test_history_timestamps_are_opt_in(history_client, args):
    client, _ = history_client
    _serve(client, [(START, "first", {}), (START + 1, "second", {})])
    result = _invoke("--start", str(START), "--end", str(END), "--timestamps", *args)

    assert result.exit_code == 0, result.output
    assert "2024-01-01 00:00:00 UTC first" in result.output
    assert result.output.index("UTC first") < result.output.index("UTC second")


@pytest.mark.parametrize("earlier_count", [0, 9998])
def test_history_preserves_identical_lines_within_and_across_pages(
    history_client, earlier_count
):
    client, _ = history_client
    entries = [(START + i, f"line-{i}", {}) for i in range(earlier_count)]
    entries += [(START + 15_000, "repeated", {"node": "a"})] * 3
    entries += [(START + 15_000, "repeated", {"node": "b"})]
    _serve(client, entries)
    result = _invoke("--start", str(START), "--end", str(END))

    assert result.exit_code == 0, result.output
    assert result.output.splitlines().count("repeated") == 4


@pytest.mark.parametrize("args", [[], ["--limit", "2"]])
def test_history_preserves_slurm_log_text(history_client, args):
    client, _ = history_client
    lines = ['hello "world" [red]', '{"message":"hello"}']
    _serve(client, [(START + i, line, {}) for i, line in enumerate(lines)])
    result = _invoke("--start", str(START), "--end", str(END), *args)

    assert result.exit_code == 0, result.output
    for line in lines:
        assert line in result.output.splitlines()


def test_history_reports_failed_windows_after_shared_retries(history_client):
    client, api = history_client
    client.log.get_log.side_effect = RuntimeError("query unavailable")
    with patch.object(log_module, "_interruptible_sleep"):
        result = _invoke("--start", str(START), "--end", str(END))

    assert result.exit_code == 2, result.output
    assert "Partial result" in result.output
    assert client.log.get_log.call_count == 5
    api.get_logs.assert_not_called()


def test_history_reports_output_failure(history_client):
    client, _ = history_client
    _serve(client, [(START, "first", {})])
    with patch(
        "leptonai.cli.slurm._print_log_line", side_effect=OSError("sink failed")
    ):
        result = _invoke("--start", str(START), "--end", str(END))

    assert result.exit_code == 1, result.output
    assert "Failed to write logs" in result.output


def test_follow_keeps_its_default_tail_and_polling(history_client):
    client, api = history_client
    with patch("leptonai.cli.slurm.time.sleep", side_effect=KeyboardInterrupt):
        result = _invoke("--follow")

    assert result.exit_code == 0, result.output
    calls = api.get_logs.call_args_list
    assert [call.kwargs["direction"] for call in calls] == ["backward", "forward"]
    assert all(call.kwargs["limit"] == 100 for call in calls)
    assert abs(calls[0].kwargs["end"] - calls[0].kwargs["start"] - 300 * 10**9) < 10**9
    client.log.get_log.assert_not_called()


@pytest.mark.parametrize("args", [("--end", str(END)), ("--workers", "2")])
def test_follow_rejects_historical_window_options(history_client, args):
    client, api = history_client
    result = _invoke("--follow", *args)

    assert result.exit_code != 0
    client.log.get_log.assert_not_called()
    api.get_logs.assert_not_called()


def test_log_with_cluster_and_id_honors_include_archived(history_client):
    client, api = history_client
    # The alive-only query does not return the archived job.
    api.list_cluster_jobs.side_effect = lambda cluster_id, job_query_mode, q: (
        [JOBS.jobs[0]] if job_query_mode == "alive_and_archive" else []
    )
    selector = ("--id", "42", "--cluster", "cluster-a")
    window = ("--start", str(START), "--end", str(END))

    default = _invoke(*window, selector=selector)
    archived = _invoke(*window, "--include-archived", selector=selector)

    assert default.exit_code == 1, default.output
    assert "No alive Slurm job found" in default.output
    assert archived.exit_code == 0, archived.output
