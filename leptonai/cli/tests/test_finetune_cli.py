"""Tests for the `lep finetune list` filters."""

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
