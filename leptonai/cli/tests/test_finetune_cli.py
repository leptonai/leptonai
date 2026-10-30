"""Tests for `lep finetune`: disabled in the CLI, plus the preserved list filters."""

import os
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

from click.testing import CliRunner

from leptonai.cli.finetune import finetune


def _invoke(args):
    client = SimpleNamespace(
        finetune=SimpleNamespace(list_all=Mock(return_value=[])),
        get_dashboard_base_url=lambda: None,
    )
    with patch("leptonai.cli.finetune.APIClient", return_value=client):
        result = CliRunner().invoke(finetune, ["list", *args])
    return result, client.finetune.list_all


def test_finetune_list_merges_labels_into_the_label_selector_query():
    result, list_all = _invoke(
        ["--query", "owner=alice", "-l", "team:research", "--label", "env"]
    )
    assert result.exit_code == 0, result.output
    assert list_all.call_args.kwargs["query"] == "owner=alice,team=research,env"


def test_finetune_list_without_labels_keeps_query_untouched():
    result, list_all = _invoke(["--status", "Running", "--status", "Queueing"])
    assert result.exit_code == 0, result.output
    kwargs = list_all.call_args.kwargs
    assert kwargs["query"] is None
    assert kwargs["status"] == ["Running", "Queueing"]
    assert kwargs["job_query_mode"] == "alive_only"


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


def test_finetune_list_keeps_legacy_q_flag():
    result, list_all = _invoke(["--q", "llama"])
    assert result.exit_code == 0, result.output
    assert list_all.call_args.kwargs["q"] == "llama"
    assert list_all.call_args.kwargs["created_by"] is None


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


def test_finetune_list_trainers_filters_by_trainer_id():
    result = _invoke_trainers(["-q", "RL"])
    assert result.exit_code == 0, result.output
    assert "nemo-rl" in result.output
    assert "nemo-automodel" not in result.output


def test_finetune_list_trainers_reports_when_nothing_matches():
    result = _invoke_trainers(["--search", "missing"])
    assert result.exit_code == 0, result.output
    assert "No trainers match the specified filters." in result.output


def test_lep_finetune_is_disabled_and_hidden():
    from leptonai.cli.cli import lep
    from leptonai.cli.finetune import FINETUNE_UNAVAILABLE_MESSAGE

    runner = CliRunner()
    assert "finetune" not in runner.invoke(lep, ["--help"]).output

    with patch("leptonai.cli.finetune.APIClient") as api_client:
        for args in (
            ["finetune"],
            ["finetune", "--help"],
            ["finetune", "list"],
            ["finetune", "create", "--help"],
            ["finetune", "remove", "-i", "some-job"],
        ):
            result = runner.invoke(lep, args)
            assert result.exit_code == 1, (args, result.output)
            assert FINETUNE_UNAVAILABLE_MESSAGE in result.output, args
    api_client.assert_not_called()


def test_lep_job_is_still_available():
    from leptonai.cli.cli import lep

    result = CliRunner().invoke(lep, ["job", "--help"])
    assert result.exit_code == 0, result.output
