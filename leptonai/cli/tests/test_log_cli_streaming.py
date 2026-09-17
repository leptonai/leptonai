"""Top-level log command: streaming lifecycle and historical parameter propagation."""

import importlib
from unittest.mock import Mock

import pytest
import requests
from click.testing import CliRunner

from leptonai.api.v2.log import LogAPI

log_module = importlib.import_module("leptonai.cli.log")


@pytest.fixture
def client(monkeypatch):
    fake = Mock()
    monkeypatch.setattr(log_module, "APIClient", lambda: fake)
    return fake


def invoke(args):
    return CliRunner().invoke(log_module.log, ["get", *args])


def history(*entries):
    return {
        "data": {
            "result": (
                [{"stream": {}, "values": [[str(ts), text] for ts, text in entries]}]
                if entries
                else []
            )
        }
    }


def test_follow_uses_one_request_without_history_preflight(client):
    closed = []

    def chunks():
        try:
            yield "[red]literal[/red]\n"
            yield "你好\n"
        finally:
            closed.append(True)

    client.log.get_log.return_value = chunks()
    result = invoke(["--endpoint", "ep", "--replica", "r", "--follow"])
    assert result.exit_code == 0, result.output
    assert result.output == "[red]literal[/red]\n你好\n"
    options = client.log.get_log.call_args.kwargs
    assert options["stream"] is True
    assert options["timestamps"] is True
    assert options["replica"] == "r"
    assert "start" not in options and "end" not in options
    client.log.get_log.assert_called_once()
    client.deployment.get.assert_not_called()
    client.deployment.get_replicas.assert_not_called()
    assert closed == [True]


@pytest.mark.parametrize("timestamp_flag", ["--no-timestamps", "--without-timestamp"])
def test_follow_file_is_flushed_before_next_chunk(client, tmp_path, timestamp_flag):
    path = tmp_path / "logs.txt"

    def chunks():
        yield "first\n"
        assert path.read_text() == "first\n"
        yield "second\n"

    client.log.get_log.return_value = chunks()
    result = invoke(
        ["--job", "j", "--replica", "r", "-f", "--path", str(path), timestamp_flag]
    )
    assert result.exit_code == 0, result.output
    assert path.read_text() == "first\nsecond\n"
    assert client.log.get_log.call_args.kwargs["timestamps"] is False
    client.job.get.assert_not_called()


@pytest.mark.parametrize(
    "error,exit_code",
    [(KeyboardInterrupt(), 0), (requests.ConnectionError("dropped"), 1)],
)
def test_follow_closes_on_interrupt_or_disconnect(client, error, exit_code):
    closed = []

    def chunks():
        try:
            yield "first\n"
            raise error
        finally:
            closed.append(True)

    client.log.get_log.return_value = chunks()
    result = invoke(["--dynamo", "dyn", "--replica", "r", "-f"])
    assert result.exit_code == exit_code, result.output
    assert "first" in result.output
    assert ("Disconnected" if exit_code == 0 else "dropped") in result.output
    assert closed == [True]


@pytest.mark.parametrize(
    "args",
    [
        ["--endpoint", "ep", "--follow"],
        ["--endpoint", "ep", "--replica", "r", "--follow", "--start", "today"],
        ["--endpoint", "ep", "--replica", "r", "--follow", "--end", "now"],
        ["--endpoint", "ep", "--replica", "r", "--follow", "--level", "error"],
        ["--endpoint", "ep", "--replica", "r", "--follow", "--limit", "10"],
        ["--endpoint", "ep", "--replica", "r", "--follow", "--workers", "2"],
        ["--endpoint", "ep", "--replica", "r", "--follow", "--direction", "forward"],
        ["--slurm-namespace", "ns", "--slurm-cluster", "sc", "--replica", "r", "-f"],
        ["--dev-pod", "dev", "--job", "j"],
        ["--ray-cluster", "ray", "--component", "worker"],
        ["--endpoint", "ep", "--ray-job-id", "j"],
        ["--slurm-cluster", "sc"],
    ],
)
def test_invalid_flags_fail_without_network(client, args):
    result = invoke(args)
    assert result.exit_code != 0
    assert client.mock_calls == []


@pytest.mark.parametrize(
    "args,expected",
    [
        (
            ["--endpoint", "ep", "--component", "worker"],
            {"name_or_deployment": "ep", "component": "worker"},
        ),
        (["--dev-pod", "dev"], {"name_or_dev_pod": "dev"}),
        (
            [
                "--ray-cluster",
                "rc",
                "--ray-job-id",
                "j",
                "--ray-component",
                "worker",
                "--ray-node-id",
                "n",
            ],
            {
                "name_or_ray_cluster": "rc",
                "ray_job_id": "j",
                "ray_component": "worker",
                "ray_node_id": "n",
            },
        ),
        (
            [
                "--slurm-namespace",
                "ns",
                "--slurm-cluster",
                "sc",
                "--slurm-job",
                "1",
                "--slurm-attempt",
                "0",
            ],
            {
                "slurm_namespace": "ns",
                "slurm_cluster": "sc",
                "slurm_job": "1",
                "slurm_attempt": "0",
            },
        ),
    ],
)
def test_filters_reach_probe_and_historical_fetch(client, args, expected):
    timestamp = 1704067201000000000
    client.log.get_log.return_value = history((timestamp, "one"))
    result = invoke([
        *args,
        "--start",
        "2024-01-01",
        "--end",
        "2024-01-02",
        "--limit",
        "1",
        "--level",
        "error,warn",
        "--query",
        "err",
        "--direction",
        "forward",
    ])
    assert result.exit_code == 0, result.output
    assert client.log.get_log.call_count == 2
    for call in client.log.get_log.call_args_list:
        for key, value in expected.items():
            assert call.kwargs[key] == value
        assert call.kwargs["level"] == "error,warn"
        assert call.kwargs["q"] == "err"
        assert call.kwargs["direction"] == "forward"


@pytest.mark.parametrize("direction", ["forward", "backward"])
def test_limited_history_pagination_and_chronological_output(client, direction):
    start = 1704067200000000000
    entries = [(start + i * 1000000000, f"line-{i}") for i in range(1, 4)]
    selected = entries if direction == "forward" else list(reversed(entries))
    client.log.get_log.side_effect = [
        history(selected[0]),
        *[history(entry) for entry in selected],
    ]
    result = invoke([
        "--dev-pod",
        "dev",
        "--start",
        str(start),
        "--end",
        str(start + 5000000000),
        "--limit",
        "3",
        "--direction",
        direction,
    ])
    assert result.exit_code == 0, result.output
    assert (
        result.output.index("line-1")
        < result.output.index("line-2")
        < result.output.index("line-3")
    )
    calls = client.log.get_log.call_args_list
    assert len(calls) == 4
    if direction == "forward":
        assert calls[2].kwargs["start"] == entries[0][0] + 1
        assert calls[3].kwargs["start"] == entries[1][0] + 1
    else:
        assert calls[2].kwargs["end"] == entries[2][0]
        assert calls[3].kwargs["end"] == entries[1][0]


@pytest.mark.parametrize("direction", ["forward", "backward"])
def test_adaptive_children_propagate_filters_and_timeout(
    client, monkeypatch, direction
):
    start = 1704067200000000000
    end = start + 2000000000
    monkeypatch.setattr(log_module, "_ADAPTIVE_PAGE_LIMIT", 2)
    entries = [
        (start + 1, "line-1"),
        (start + 2, "line-2"),
        (start + 1500000000, "line-3"),
    ]

    def query(**kwargs):
        return history(
            *[
                entry
                for entry in entries
                if kwargs["start"] <= entry[0] < kwargs["end"]
            ][: kwargs["limit"]]
        )

    client.log.get_log.side_effect = query
    result = invoke([
        "--ray-cluster",
        "ray",
        "--ray-component",
        "worker",
        "--level",
        "error",
        "--query",
        "needle",
        "--direction",
        direction,
        "--timeout",
        "7",
        "--start",
        str(start),
        "--end",
        str(end),
        "--workers",
        "2",
    ])
    assert result.exit_code == 0, result.output
    assert (
        result.output.index("line-1")
        < result.output.index("line-2")
        < result.output.index("line-3")
    )
    assert client.log.get_log.call_count == 3
    for call in client.log.get_log.call_args_list:
        assert call.kwargs["name_or_ray_cluster"] == "ray"
        assert call.kwargs["ray_component"] == "worker"
        assert call.kwargs["level"] == "error"
        assert call.kwargs["q"] == "needle"
        assert call.kwargs["timeout"] == 7
        assert call.kwargs["direction"] == "forward"


def test_archived_replica_history_is_not_checked_against_live_replicas(client):
    client.log.get_log.return_value = history()
    result = invoke([
        "--job",
        "j",
        "--replica",
        "old",
        "--query",
        "error",
        "--job-query-mode",
        "archive_only",
        "--job-history-name",
        "j-gen1",
        "--start",
        "2024-01-01",
        "--end",
        "2024-01-02",
    ])
    assert result.exit_code == 0, result.output
    options = client.log.get_log.call_args.kwargs
    assert options["job_query_mode"] == "archive_only"
    assert options["job_history_name"] == "j-gen1"
    client.job.get_replicas.assert_not_called()


@pytest.mark.parametrize("query_args", [[], ["--query", "ignored"]])
def test_cli_follow_through_real_sdk(client, query_args):
    response = Mock(status_code=200, headers={"Content-Type": "text/plain"})
    response.iter_content.return_value = iter([b"first\n", "中文\n".encode()])
    client._get.return_value = response
    client.log = LogAPI(client)
    result = invoke(["--dev-pod", "dev", "--replica", "r", "--follow", *query_args])
    assert result.exit_code == 0, result.output
    assert result.output == "first\n中文\n"
    assert client._get.call_args.args == ("/logs",)
    assert client._get.call_args.kwargs["params"]["dev_pod"] == "dev"
    assert client._get.call_args.kwargs["stream"] is True
    assert "q" not in client._get.call_args.kwargs["params"]
    response.close.assert_called_once()


def test_follow_timeout_reaches_sdk(client):
    client.log.get_log.return_value = (chunk for chunk in ["first\n"])
    result = invoke(["--job", "j", "--replica", "r", "-f", "--timeout", "5"])
    assert result.exit_code == 0, result.output
    assert client.log.get_log.call_args.kwargs["timeout"] == 5


def test_job_name_resolution_honors_archive_mode(client, monkeypatch):
    job = Mock()
    job.metadata.id_ = "job-id"
    resolver = Mock(return_value=job)
    monkeypatch.setattr(log_module, "_get_newest_job_by_name", resolver)
    client.log.get_log.return_value = history()
    result = invoke([
        "--job-name",
        "job-name",
        "--job-query-mode",
        "archive_only",
        "--start",
        "2024-01-01",
        "--end",
        "2024-01-02",
    ])
    assert result.exit_code == 0, result.output
    resolver.assert_called_once_with("job-name", job_query_mode="archive_only")
    assert client.log.get_log.call_args.kwargs["name_or_job"] == "job-id"


@pytest.mark.parametrize(
    "query_args,expected",
    [([], ""), (["--query", "error"], "error")],
)
def test_replica_history_through_sdk_sends_query_on_every_request(
    client, query_args, expected
):
    import json

    response = requests.Response()
    response.status_code = 200
    response.headers["Content-Type"] = "application/json"
    response._content = json.dumps(
        history((1704067201000000000, "log-content"))
    ).encode()
    client.new_deployment_api_enabled = False
    client._get.return_value = response
    client.log = LogAPI(client)
    result = invoke([
        "-e",
        "ep",
        "--replica",
        "r",
        "--start",
        "2024-01-01",
        "--end",
        "2024-01-02",
        "--limit",
        "1",
        *query_args,
    ])
    assert result.exit_code == 0, result.output
    assert "log-content" in result.output
    assert client._get.call_count == 2
    for call in client._get.call_args_list:
        assert call.args == ("/logs",)
        assert call.kwargs["params"]["q"] == expected
        assert call.kwargs["params"]["replica"] == "r"


def test_replica_history_without_time_bounds_uses_default_query(client):
    client.log.get_log.return_value = history()
    result = invoke(["-e", "ep", "--replica", "r"])
    assert result.exit_code == 0, result.output
    assert client.log.get_log.call_args.kwargs["q"] == ""
    assert "No logs found" in result.output
