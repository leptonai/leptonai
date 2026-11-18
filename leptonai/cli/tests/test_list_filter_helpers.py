"""Unit tests for the shared `lep <resource> list` filter helpers."""

from types import SimpleNamespace

import click
import pytest
from click.testing import CliRunner

from leptonai.api.v2.types.deployment import LeptonDeploymentState
from leptonai.cli.util import (
    LooseChoice,
    created_by_equals,
    creator_matches,
    deployment_display_state,
    keyword_matches,
    labels_to_selector,
    node_group_matches,
    normalize_keyword,
    plural,
    prefix_matches,
    state_matches,
)


@pytest.mark.parametrize(
    "value",
    [
        "Not Ready",
        "not ready",
        "NOT READY",
        "NotReady",
        "notready",
        "not-ready",
        "not_ready",
    ],
)
def test_loose_choice_accepts_loose_spellings(value):
    choice = LooseChoice(("Ready", "Not Ready"))
    assert choice.convert(value, None, None) == "Not Ready"


def test_loose_choice_rejects_unknown_value_listing_canonical_choices():
    choice = LooseChoice(("Ready", "Not Ready"))
    with pytest.raises(click.BadParameter) as excinfo:
        choice.convert("bogus", None, None)
    assert "'bogus' is not one of 'Ready', 'Not Ready'." in str(excinfo.value)


def test_loose_choice_rejects_abbreviations():
    # Values must be whole (only case/space/hyphen/underscore are loose), like
    # picking a value in the dashboard's filter.
    choice = LooseChoice(("Running", "Stopped"))
    with pytest.raises(click.BadParameter):
        choice.convert("run", None, None)


def test_created_by_equals_is_exact_and_case_insensitive():
    md = SimpleNamespace(created_by="Alice@Example.com", owner="bob")
    assert created_by_equals(md, ()) is True
    assert created_by_equals(md, ["alice@example.com"]) is True
    assert created_by_equals(md, ["alice"]) is False
    assert created_by_equals(md, ["bob"]) is False
    assert created_by_equals(SimpleNamespace(created_by=None), ["x"]) is False


def test_deployment_display_state_prefers_phase():
    stopped = SimpleNamespace(state="Not Ready", phase=LeptonDeploymentState.Stopped)
    assert deployment_display_state(stopped) == LeptonDeploymentState.Stopped
    no_phase = SimpleNamespace(state="Ready", phase=None)
    assert deployment_display_state(no_phase) == "Ready"
    unknown_phase = SimpleNamespace(state="Ready", phase=LeptonDeploymentState.Unknown)
    assert deployment_display_state(unknown_phase) == "Ready"
    assert deployment_display_state(None) is None


def test_loose_choice_help_lists_canonical_spellings():
    @click.command()
    @click.option("--state", type=LooseChoice(("Ready", "Not Ready")))
    def cmd(state):
        click.echo(state)

    runner = CliRunner()
    help_result = runner.invoke(cmd, ["--help"])
    assert "[Ready|Not Ready]" in help_result.output
    assert "[ready|not ready]" not in help_result.output

    result = runner.invoke(cmd, ["--state", "not-ready"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "Not Ready"

    result = runner.invoke(cmd, ["--state", "bogus"])
    assert result.exit_code == 2
    assert "Invalid value for '--state': 'bogus' is not one of" in result.output
    assert "'Not Ready'" in result.output


def test_normalize_keyword_and_keyword_matches():
    assert normalize_keyword(None) == ""
    assert normalize_keyword("  Foo ") == "foo"
    assert keyword_matches("", None) is True
    assert keyword_matches("foo", None, "xFOOx") is True
    assert keyword_matches("foo", None, "bar") is False
    assert keyword_matches("foo") is False


def test_prefix_matches_is_case_insensitive_and_empty_means_no_filter():
    assert prefix_matches("Alice@Example.com", ()) is True
    assert prefix_matches("Alice@Example.com", ["alice"]) is True
    assert prefix_matches("Alice@Example.com", ["bob", "ALICE@"]) is True
    assert prefix_matches("Alice@Example.com", ["lice"]) is False
    assert prefix_matches(None, ["alice"]) is False


def test_state_matches_compares_enum_values_case_insensitively():
    assert state_matches((), None) is True
    assert state_matches(["not ready"], LeptonDeploymentState.NotReady) is True
    assert (
        state_matches(
            ["Stopped"],
            LeptonDeploymentState.NotReady,
            LeptonDeploymentState.Stopped,
        )
        is True
    )
    assert state_matches([LeptonDeploymentState.Ready], "Ready") is True
    assert state_matches(["Ready"], None) is False
    assert state_matches(["Ready"], "Starting") is False


def test_creator_matches_created_by_or_owner():
    metadata = SimpleNamespace(created_by="alice@example.com", owner="alice-id")
    assert creator_matches(metadata, ()) is True
    assert creator_matches(metadata, ["ALICE@"]) is True
    assert creator_matches(metadata, ["alice-i"]) is True
    assert creator_matches(metadata, ["bob"]) is False
    assert creator_matches(None, ["alice"]) is False


def test_node_group_matches_substring():
    affinity = SimpleNamespace(allowed_dedicated_node_groups=["H100-Cluster-abc"])
    assert node_group_matches(affinity, ()) is True
    assert node_group_matches(affinity, ["h100"]) is True
    assert node_group_matches(affinity, ["a100", "cluster-ABC"]) is True
    assert node_group_matches(affinity, ["a100"]) is False
    assert node_group_matches(None, ["h100"]) is False


@pytest.mark.parametrize(
    "labels, base_query, expected",
    [
        ((), None, None),
        (("team",), None, "team"),
        (("team:research",), None, "team=research"),
        (("team=research", "env:prod"), None, "team=research,env=prod"),
        (("tier!=gold",), None, "tier!=gold"),
        (("env in (a,b)",), None, "env in (a,b)"),
        (("team:research",), "owner=alice", "owner=alice,team=research"),
        ((), "  owner=alice ", "owner=alice"),
        (("  ",), "", None),
    ],
)
def test_labels_to_selector(labels, base_query, expected):
    assert labels_to_selector(labels, base_query=base_query) == expected


def test_plural_uses_singular_only_for_one():
    # LEP-7556: "1 pods" in the pod list summary.
    assert plural(1, "pod") == "pod"
    assert plural(0, "pod") == "pods"
    assert plural(2, "line") == "lines"
    assert plural(3, "entry", "entries") == "entries"
