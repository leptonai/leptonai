"""Tests for the `lep finetune` commands.

Fine-tune jobs are disabled in the OSS release (LEP-7170). The filter tests
re-enable the group so the preserved implementation stays covered.
"""

import os
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

import pytest
from click.testing import CliRunner

from leptonai.cli.cli import lep
from leptonai.cli.finetune import FINETUNE_UNAVAILABLE_MESSAGE, finetune


@pytest.fixture
def finetune_enabled():
    with patch("leptonai.cli.finetune.FINETUNE_ENABLED", True):
        yield


@pytest.mark.parametrize(
    "args",
    [
        ["finetune"],
        ["finetune", "list"],
        ["finetune", "get", "--id", "ft-1"],
        ["finetune", "delete", "--id", "ft-1"],
        ["finetune", "create", "--name", "ft-1"],
        ["finetune", "list-trainers"],
        ["finetune", "create", "--help"],
    ],
)
def test_finetune_commands_are_unavailable(args):
    with patch("leptonai.cli.finetune.APIClient") as api_client:
        result = CliRunner().invoke(lep, args)
    assert result.exit_code == 1, result.output
    assert FINETUNE_UNAVAILABLE_MESSAGE in result.output
    api_client.assert_not_called()


def test_lep_help_does_not_advertise_finetune():
    result = CliRunner().invoke(lep, ["--help"])
    assert result.exit_code == 0, result.output
    assert "finetune" not in result.output


def test_finetune_help_says_unavailable_and_lists_no_subcommands():
    result = CliRunner().invoke(lep, ["finetune", "--help"])
    assert result.exit_code == 0, result.output
    assert FINETUNE_UNAVAILABLE_MESSAGE in result.output
    for name in ("list", "get", "delete", "create", "list-trainers"):
        assert f"  {name} " not in result.output


def test_job_commands_remain_available():
    result = CliRunner().invoke(lep, ["job", "--help"])
    assert result.exit_code == 0, result.output
    assert "list" in result.output


def _invoke(args):
    client = SimpleNamespace(
        finetune=SimpleNamespace(list_all=Mock(return_value=[])),
        get_dashboard_base_url=lambda: None,
    )
    with patch("leptonai.cli.finetune.APIClient", return_value=client):
        result = CliRunner().invoke(finetune, ["list", *args])
    return result, client.finetune.list_all


@pytest.mark.usefixtures("finetune_enabled")
def test_finetune_list_merges_labels_into_the_label_selector_query():
    result, list_all = _invoke(
        ["--query", "owner=alice", "-l", "team:research", "--label", "env"]
    )
    assert result.exit_code == 0, result.output
    assert list_all.call_args.kwargs["query"] == "owner=alice,team=research,env"


@pytest.mark.usefixtures("finetune_enabled")
def test_finetune_list_without_labels_keeps_query_untouched():
    result, list_all = _invoke(["--status", "Running", "--status", "Queueing"])
    assert result.exit_code == 0, result.output
    kwargs = list_all.call_args.kwargs
    assert kwargs["query"] is None
    assert kwargs["status"] == ["Running", "Queueing"]
    assert kwargs["job_query_mode"] == "alive_only"


@pytest.mark.usefixtures("finetune_enabled")
def test_finetune_list_accepts_shared_filter_names():
    result, list_all = _invoke([
        "--search",
        "llama",
        "-s",
        "Running",
        "--state",
        "Failed",
        "-u",
        "alice",
        "--created-by",
        "bob",
        "-ng",
        "h100",
    ])
    assert result.exit_code == 0, result.output
    kwargs = list_all.call_args.kwargs
    assert kwargs["q"] == "llama"
    assert kwargs["status"] == ["Running", "Failed"]
    assert kwargs["created_by"] == ["alice", "bob"]
    assert kwargs["node_groups"] == ["h100"]
    assert "No finetune jobs match the specified filters." in result.output


@pytest.mark.usefixtures("finetune_enabled")
def test_finetune_list_keeps_legacy_q_flag():
    result, list_all = _invoke(["--q", "llama"])
    assert result.exit_code == 0, result.output
    assert list_all.call_args.kwargs["q"] == "llama"
    assert list_all.call_args.kwargs["created_by"] is None


@pytest.mark.usefixtures("finetune_enabled")
def test_finetune_list_without_filters_does_not_print_empty_filter_message():
    result, _ = _invoke([])
    assert result.exit_code == 0, result.output
    assert "match the specified filters" not in result.output


def _invoke_trainers(args):
    trainers = [
        SimpleNamespace(
            trainer_id="nemo-automodel", is_default=True, model_dump=lambda: {}
        ),
        SimpleNamespace(trainer_id="nemo-rl", is_default=False, model_dump=lambda: {}),
    ]
    client = SimpleNamespace(
        finetune=SimpleNamespace(list_trainers=Mock(return_value=trainers))
    )
    with patch("leptonai.cli.finetune.APIClient", return_value=client):
        return CliRunner().invoke(finetune, ["list-trainers", *args])


@pytest.mark.usefixtures("finetune_enabled")
def test_finetune_list_trainers_filters_by_trainer_id():
    result = _invoke_trainers(["-q", "RL"])
    assert result.exit_code == 0, result.output
    assert "nemo-rl" in result.output
    assert "nemo-automodel" not in result.output


@pytest.mark.usefixtures("finetune_enabled")
def test_finetune_list_trainers_reports_when_nothing_matches():
    result = _invoke_trainers(["--search", "missing"])
    assert result.exit_code == 0, result.output
    assert "No trainers match the specified filters." in result.output


@pytest.mark.usefixtures("finetune_enabled")
def test_finetune_list_state_takes_the_dashboard_values():
    result, list_all = _invoke(["--status", "not-a-state"])
    assert result.exit_code == 2
    list_all.assert_not_called()
    result, list_all = _invoke(["-s", "running"])
    assert result.exit_code == 0, result.output
    assert list_all.call_args.kwargs["status"] == ["Running"]


@pytest.mark.usefixtures("finetune_enabled")
def test_finetune_list_passes_creator_through_without_local_matching():
    # The dashboard sends created_by to the server and shows what it returns.
    from leptonai.api.v2.types.common import Metadata
    from leptonai.api.v2.types.finetune import LeptonFineTuneJob

    job = LeptonFineTuneJob(metadata=Metadata(id="j", name="j", created_by="malice@x"))
    client = SimpleNamespace(
        finetune=SimpleNamespace(list_all=Mock(return_value=[job])),
        get_dashboard_base_url=lambda: None,
    )
    with patch("leptonai.cli.finetune.APIClient", return_value=client):
        result = CliRunner().invoke(finetune, ["list", "-u", "alice"])
    assert result.exit_code == 0, result.output
    assert client.finetune.list_all.call_args.kwargs["created_by"] == ["alice"]
    assert "No finetune jobs match" not in result.output
