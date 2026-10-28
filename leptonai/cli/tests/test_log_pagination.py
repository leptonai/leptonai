"""Log pagination must finish a timestamp before moving past it."""

import importlib
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from leptonai.api.v2.types.slurm import SlurmLogs
from leptonai.cli import lep
from leptonai.cli.tests._log_test_helpers import loki_response
from leptonai.cli.tests.test_slurm_cli import _fake_client


log_module = importlib.import_module("leptonai.cli.log")
START = 1_704_067_200_000_000_000
END = START + 30_000
BOUNDARY = START + 15_000


def _query(entries, **kwargs):
    selected = [
        entry for entry in entries if kwargs["start"] <= entry[0] < kwargs["end"]
    ]
    selected.sort(
        key=lambda entry: entry[0], reverse=kwargs.get("direction") == "backward"
    )
    return loki_response(selected[: kwargs["limit"]])


@pytest.mark.parametrize(
    "selector", ["--endpoint", "--job", "--dev-pod", "--ray-cluster", "--dynamo"]
)
@pytest.mark.parametrize("direction", ["forward", "backward"])
def test_limited_history_preserves_page_boundary(selector, direction, tmp_path):
    # Only two entries share a timestamp. They straddle the 10,000-row page
    # boundary and are intentionally identical, so a set-based dedup loses one.
    base = START if direction == "forward" else BOUNDARY
    entries = [(base + i, f"line-{i}", {}) for i in range(1, 10_000)]
    entries += [(BOUNDARY, "boundary", {})] * 2
    client = Mock()
    client.log.get_log.side_effect = lambda **kwargs: _query(entries, **kwargs)
    output = tmp_path / "logs.txt"
    with patch.object(log_module, "APIClient", return_value=client):
        result = CliRunner().invoke(
            log_module.log,
            [
                "get",
                selector,
                "workload",
                "--start",
                str(START),
                "--end",
                str(END),
                "--limit",
                "10001",
                "--direction",
                direction,
                "--without-timestamp",
                "--path",
                str(output),
            ],
        )
    assert result.exit_code == 0, result.output
    lines = output.read_text().splitlines()
    assert lines.count("boundary") == 2
    assert sum(line.startswith("line-") for line in lines) == 9999


@pytest.mark.parametrize(
    "entries",
    [
        [
            (START + 1, "first", {}),
            (START + 2, "boundary", {}),
            (START + 2, "boundary", {}),
            (START + 3, "last", {}),
        ],
        [(START + 1, "repeated", {})] * 3,
        [(START + 1, "same-text", {"node": node}) for node in ("a", "b", "c")],
    ],
)
def test_slurm_follow_finishes_boundary_before_advancing(entries):
    client, api = _fake_client()
    api.get_logs.side_effect = lambda _cluster, **kwargs: SlurmLogs(
        **_query(entries, **kwargs)
    )
    with (
        patch("leptonai.cli.slurm.APIClient", return_value=client),
        patch("leptonai.cli.slurm.time.time_ns", return_value=END),
        patch("leptonai.cli.slurm.time.sleep", side_effect=KeyboardInterrupt),
    ):
        result = CliRunner().invoke(
            lep,
            [
                "slurm",
                "job",
                "log",
                "-i",
                "42",
                "--follow",
                "--limit",
                "2",
                "--start",
                str(START),
            ],
        )
    assert result.exit_code == 0, result.output
    output = result.output.splitlines()
    expected = [line for _, line, _ in sorted(entries, key=lambda entry: entry[0])]
    assert output[: len(expected)] == expected
    assert len(output) == len(expected) + 1  # interruption message


@pytest.mark.parametrize("direction", ["forward", "backward"])
@pytest.mark.parametrize("limit", [2, 10_000, 10_001])
def test_limited_history_single_timestamp_respects_total_or_reports_cap(
    direction, limit, tmp_path
):
    entries = [(BOUNDARY, "same-timestamp", {})] * 10_001
    client = Mock()
    client.log.get_log.side_effect = lambda **kwargs: _query(entries, **kwargs)
    output = tmp_path / "logs.txt"
    with patch.object(log_module, "APIClient", return_value=client):
        result = CliRunner().invoke(
            log_module.log,
            [
                "get",
                "--endpoint",
                "ep",
                "--start",
                str(START),
                "--end",
                str(END),
                "--limit",
                str(limit),
                "--direction",
                direction,
                "--without-timestamp",
                "--path",
                str(output),
            ],
        )
    if limit > 10_000:
        assert result.exit_code != 0
        assert "cannot paginate" in result.output
        assert not output.exists()
    else:
        assert result.exit_code == 0, result.output
        assert output.read_text().splitlines().count("same-timestamp") == limit


def test_slurm_follow_reports_a_full_single_timestamp_at_the_api_limit():
    entries = [(BOUNDARY, "same-timestamp", {})] * 10_001
    client, api = _fake_client()
    api.get_logs.side_effect = lambda _cluster, **kwargs: SlurmLogs(
        **_query(entries, **kwargs)
    )
    with (
        patch("leptonai.cli.slurm.APIClient", return_value=client),
        patch("leptonai.cli.slurm.time.time_ns", return_value=END),
        patch("leptonai.cli.slurm.time.sleep", side_effect=KeyboardInterrupt),
    ):
        result = CliRunner().invoke(
            lep,
            [
                "slurm",
                "job",
                "log",
                "-i",
                "42",
                "--follow",
                "--limit",
                "5000",
                "--start",
                str(START),
            ],
        )
    assert result.exit_code != 0
    assert "cannot paginate" in result.output
    assert "same-timestamp" not in result.output
    assert [call.kwargs["limit"] for call in api.get_logs.call_args_list] == [
        5000,
        10000,
    ]
