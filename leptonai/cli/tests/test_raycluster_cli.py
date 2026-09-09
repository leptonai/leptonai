"""Tests for the `lep raycluster list` and `lep raycluster list-jobs` filters."""

import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

import pytest
from click.testing import CliRunner
from ray.job_submission import JobStatus

from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.raycluster import (
    LeptonRayCluster,
    LeptonRayClusterStatus,
    LeptonRayClusterUserSpec,
)
from leptonai.cli.raycluster import (
    _filter_ray_jobs,
    _filter_rayclusters,
    console as raycluster_console,
    raycluster,
)


def _cluster(name, *, state="Ready", created_by=None):
    return LeptonRayCluster(
        metadata=Metadata(
            id=f"{name}-id",
            name=name,
            created_at=1000,
            created_by=created_by,
            owner=created_by,
        ),
        spec=LeptonRayClusterUserSpec(),
        status=LeptonRayClusterStatus(state=state),
    )


@pytest.fixture
def clusters():
    return [
        _cluster("Alpha-Ray", state="Ready", created_by="alice@example.com"),
        _cluster("beta-ray", state="Not Ready", created_by="bob@example.com"),
        _cluster("gamma", state="Stopped", created_by="alice@example.com"),
    ]


def _names(items):
    return [item.metadata.name for item in items]


def test_filter_rayclusters_keyword_matches_name_or_id_case_insensitively(clusters):
    assert _names(_filter_rayclusters(clusters, keyword="RAY")) == [
        "Alpha-Ray",
        "beta-ray",
    ]
    assert _names(_filter_rayclusters(clusters, keyword="gamma-id")) == ["gamma"]


def test_filter_rayclusters_state_and_creator_combine_with_and(clusters):
    assert _names(_filter_rayclusters(clusters, states=["Not Ready"])) == ["beta-ray"]
    assert _names(
        _filter_rayclusters(clusters, states=["ready", "stopped"], creators=["alice"])
    ) == ["Alpha-Ray", "gamma"]
    assert _filter_rayclusters(clusters, names=["gamma"], states=["Ready"]) == []


def _ray_job(submission_id=None, job_id=None, entrypoint=None, status=None):
    return SimpleNamespace(
        submission_id=submission_id,
        job_id=job_id,
        entrypoint=entrypoint,
        status=status,
        start_time=None,
        end_time=None,
        message=None,
    )


def test_filter_ray_jobs_matches_id_entrypoint_and_status():
    jobs = [
        _ray_job("raysubmit_1", None, "python train.py", JobStatus.RUNNING),
        _ray_job("raysubmit_2", None, "python eval.py", JobStatus.FAILED),
        _ray_job(None, "03000000", "bash run.sh", "SUCCEEDED"),
    ]
    assert [j.entrypoint for j in _filter_ray_jobs(jobs, keyword="PYTHON")] == [
        "python train.py",
        "python eval.py",
    ]
    assert [j.job_id for j in _filter_ray_jobs(jobs, keyword="0300")] == ["03000000"]
    assert [
        j.entrypoint for j in _filter_ray_jobs(jobs, statuses=["FAILED", "SUCCEEDED"])
    ] == ["python eval.py", "bash run.sh"]
    assert _filter_ray_jobs(jobs, keyword="train", statuses=["FAILED"]) == []


def _invoke_list(items, args):
    fake_client = SimpleNamespace(raycluster=SimpleNamespace(list_all=lambda: items))
    with patch("leptonai.cli.raycluster.APIClient", return_value=fake_client):
        return CliRunner().invoke(raycluster, ["list", *args])


def test_raycluster_list_applies_filters(clusters, monkeypatch):
    monkeypatch.setattr(raycluster_console, "width", 400)
    result = _invoke_list(
        clusters, ["-u", "alice", "--state", "not-ready", "--state", "stopped"]
    )
    assert result.exit_code == 0, result.output
    assert "gamma" in result.output
    assert "Alpha-Ray" not in result.output
    assert "beta-ray" not in result.output


def test_raycluster_list_reports_when_nothing_matches(clusters):
    result = _invoke_list(clusters, ["--search", "nothing"])
    assert result.exit_code == 0, result.output
    assert "No Ray clusters match the specified filters." in result.output


def test_raycluster_list_rejects_unknown_state(clusters):
    result = _invoke_list(clusters, ["--state", "bogus"])
    assert result.exit_code == 2
    assert "Invalid value for '--state'" in result.output


def test_raycluster_list_jobs_applies_filters(monkeypatch):
    monkeypatch.setattr(raycluster_console, "width", 240)
    jobs = [
        _ray_job("raysubmit_train", None, "python train.py", JobStatus.RUNNING),
        _ray_job("raysubmit_eval", None, "python eval.py", JobStatus.FAILED),
    ]
    fake_client = SimpleNamespace(
        raycluster=SimpleNamespace(get=lambda name: object()),
        url="https://example.com/api/v2/workspaces/ws",
        token=lambda: "token",
        get_dashboard_base_url=lambda: "https://dashboard.example.com",
    )
    fake_submission = SimpleNamespace(list_jobs=lambda: jobs)
    with patch("leptonai.cli.raycluster.APIClient", return_value=fake_client):
        with patch(
            "leptonai.cli.raycluster.JobSubmissionClient",
            return_value=fake_submission,
        ):
            result = CliRunner().invoke(
                raycluster,
                ["list-jobs", "-n", "my-cluster", "--status", "failed"],
            )
            no_match = CliRunner().invoke(
                raycluster,
                ["list-jobs", "-n", "my-cluster", "-q", "train", "-s", "failed"],
            )
    assert result.exit_code == 0, result.output
    assert "raysubmit_eval" in result.output
    assert "raysubmit_train" not in result.output
    assert no_match.exit_code == 0, no_match.output
    assert "No Ray jobs match the specified filters on this cluster." in no_match.output
