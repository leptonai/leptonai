"""Tests for the `lep pod list` filters."""

import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

import pytest
from click.testing import CliRunner

from leptonai.api.v2.types.affinity import LeptonResourceAffinity
from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.deployment import (
    LeptonContainer,
    LeptonDeployment,
    LeptonDeploymentStatus,
    LeptonDeploymentUserSpec,
    ResourceRequirement,
)
from leptonai.cli.pod import _filter_pods, console as pod_console, pod


def _pod(name, *, state="Ready", phase=None, created_by=None, node_groups=None):
    affinity = (
        LeptonResourceAffinity(allowed_dedicated_node_groups=list(node_groups))
        if node_groups
        else None
    )
    return LeptonDeployment(
        metadata=Metadata(
            id=f"{name}-id",
            name=name,
            created_at=1000,
            created_by=created_by,
            owner=created_by,
        ),
        spec=LeptonDeploymentUserSpec(
            is_pod=True,
            container=LeptonContainer(image="ubuntu"),
            resource_requirement=ResourceRequirement(
                resource_shape="cpu.small", min_replicas=1, affinity=affinity
            ),
        ),
        status=LeptonDeploymentStatus(
            state=state,
            phase=phase,
            endpoint={"internal_endpoint": "", "external_endpoint": ""},
            container_port_status=None,
        ),
    )


@pytest.fixture
def pods():
    return [
        _pod(
            "Dev-Box",
            state="Ready",
            created_by="alice@example.com",
            node_groups=["h100-cluster"],
        ),
        _pod(
            "notebook",
            state="Not Ready",
            phase="Stopped",
            created_by="bob@example.com",
            node_groups=["a100-cluster"],
        ),
        _pod("scratch-box", state="Starting", created_by="alice@example.com"),
    ]


def _names(items):
    return [item.metadata.name for item in items]


def test_filter_pods_pattern_is_a_regex_on_the_name(pods):
    assert _names(_filter_pods(pods, pattern="^(Dev|scratch)")) == [
        "Dev-Box",
        "scratch-box",
    ]
    assert _names(_filter_pods(pods, pattern="box$")) == ["scratch-box"]


def test_filter_pods_keyword_matches_name_or_id_case_insensitively(pods):
    assert _names(_filter_pods(pods, keyword="BOX")) == ["Dev-Box", "scratch-box"]
    assert _names(_filter_pods(pods, keyword="notebook-id")) == ["notebook"]


def test_filter_pods_state_matches_displayed_state_or_phase(pods):
    assert _names(_filter_pods(pods, states=["Stopped"])) == ["notebook"]
    assert _names(_filter_pods(pods, states=["Not Ready"])) == ["notebook"]
    assert _names(_filter_pods(pods, states=["ready", "starting"])) == [
        "Dev-Box",
        "scratch-box",
    ]


def test_filter_pods_combines_creator_node_group_and_state_with_and(pods):
    assert _names(_filter_pods(pods, creators=["alice"], node_groups=["h100"])) == [
        "Dev-Box"
    ]
    assert _filter_pods(pods, creators=["alice"], states=["Not Ready"]) == []


def _invoke_pod_list(items, args):
    fake_client = SimpleNamespace(
        pod=SimpleNamespace(list_all=lambda: items),
        get_dashboard_base_url=lambda: None,
    )
    with patch("leptonai.cli.pod.APIClient", return_value=fake_client):
        with patch(
            "leptonai.cli.pod._get_only_replica_public_ip",
            return_value="203.0.113.7",
        ):
            return CliRunner().invoke(pod, ["list", *args])


def test_pod_list_applies_filters(pods, monkeypatch):
    monkeypatch.setattr(pod_console, "width", 240)
    result = _invoke_pod_list(
        pods, ["-u", "alice", "-s", "ready", "-s", "starting", "-ng", "h100"]
    )
    assert result.exit_code == 0, result.output
    assert "Dev-Box" in result.output
    assert "scratch-box" not in result.output
    assert "notebook" not in result.output


def test_pod_list_combines_pattern_with_the_other_filters(pods, monkeypatch):
    monkeypatch.setattr(pod_console, "width", 240)
    result = _invoke_pod_list(pods, ["--pattern", "box$", "--state", "starting"])
    assert result.exit_code == 0, result.output
    assert "scratch-box" in result.output
    assert "Dev-Box" not in result.output
    assert "notebook" not in result.output


def test_pod_list_rejects_invalid_pattern(pods):
    result = _invoke_pod_list(pods, ["--pattern", "["])
    assert result.exit_code == 2
    assert "Invalid value for '--pattern'" in result.output
    assert "invalid regular expression" in result.output


def test_pod_list_rejects_unknown_state(pods):
    result = _invoke_pod_list(pods, ["--state", "bogus"])
    assert result.exit_code == 2
    assert "Invalid value for '--state'" in result.output


def test_pod_list_reports_when_no_pod_matches(pods):
    result = _invoke_pod_list(pods, ["--search", "nothing"])
    assert result.exit_code == 0, result.output
    assert "No pods match the specified filters." in result.output


def test_pod_list_keeps_empty_workspace_message_without_filters():
    result = _invoke_pod_list([], [])
    assert result.exit_code == 0, result.output
    assert "No pods found. Use `lep pod create` to create pods." in result.output
