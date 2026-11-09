"""Tests for Ray cluster filters and authenticated job requests."""

import json
import os
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

import pytest
import responses
from click.testing import CliRunner
from ray.job_submission import JobSubmissionClient

from leptonai.api.v2.workspace_record import WorkspaceRecord, _LocalWorkspaceRecord
from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.raycluster import (
    LeptonRayCluster,
    LeptonRayClusterStatus,
    LeptonRayClusterUserSpec,
    LeptonRayJob,
)
from leptonai.cli.client import APIClient
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


def test_filter_rayclusters_applies_only_the_cli_only_name_filter(clusters):
    # Case-insensitive substrings, ORed; no filter keeps everything.
    assert _names(_filter_rayclusters(clusters, names=["RAY"])) == [
        "Alpha-Ray",
        "beta-ray",
    ]
    assert _names(_filter_rayclusters(clusters, names=["gamma", "ALPHA"])) == [
        "Alpha-Ray",
        "gamma",
    ]
    assert _names(_filter_rayclusters(clusters)) == ["Alpha-Ray", "beta-ray", "gamma"]


def _ray_job(job_id, state=None, entrypoint="python run.py"):
    return LeptonRayJob(
        metadata={"id": job_id, "name": job_id},
        spec={"entrypoint": entrypoint},
        status=None if state is None else {"state": state},
    )


def _job_ids(jobs):
    return [job.metadata.id_ for job in jobs]


def test_filter_ray_jobs_matches_like_the_dashboard_jobs_tab():
    jobs = [
        _ray_job("raysubmit_train", "Running", "python train.py"),
        _ray_job("raysubmit_eval", "Failed", "python eval.py"),
        _ray_job("03000000", "Completed", "bash run.sh"),
        _ray_job("raysubmit_new"),
    ]
    # The search matches the job ID or name only, not the entrypoint.
    assert _job_ids(_filter_ray_jobs(jobs, keyword="EVAL")) == ["raysubmit_eval"]
    assert _filter_ray_jobs(jobs, keyword="python") == []
    assert _job_ids(_filter_ray_jobs(jobs, keyword="0300")) == ["03000000"]
    # The state filter is exact on the Lepton state; a job without a state
    # always passes it.
    assert _job_ids(_filter_ray_jobs(jobs, statuses=["Failed", "Completed"])) == [
        "raysubmit_eval",
        "03000000",
        "raysubmit_new",
    ]
    assert _job_ids(_filter_ray_jobs(jobs, statuses=["Awaiting"])) == ["raysubmit_new"]
    assert _filter_ray_jobs(jobs, keyword="train", statuses=["Failed"]) == []


def _invoke_list(items, args):
    calls = []

    def list_all(**kwargs):
        calls.append(kwargs)
        return items

    fake_client = SimpleNamespace(raycluster=SimpleNamespace(list_all=list_all))
    with patch("leptonai.cli.raycluster.APIClient", return_value=fake_client):
        result = CliRunner().invoke(raycluster, ["list", *args])
    return result, calls


def test_raycluster_list_sends_no_filters_by_default(clusters):
    result, calls = _invoke_list(clusters, [])
    assert result.exit_code == 0, result.output
    assert calls == [{"q": None, "status": None, "created_by": None}]


def test_raycluster_list_passes_dashboard_filters_to_the_server(clusters, monkeypatch):
    monkeypatch.setattr(raycluster_console, "width", 400)
    result, calls = _invoke_list(
        clusters,
        [
            "-q",
            "Ray",
            "--state",
            "not-ready",
            "-s",
            "STOPPED",
            "-u",
            "Alice@Example.com",
        ],
    )
    assert result.exit_code == 0, result.output
    # Canonical state names, the creator as typed; the server matches them.
    assert calls == [{
        "q": "Ray",
        "status": ["Not Ready", "Stopped"],
        "created_by": ["Alice@Example.com"],
    }]
    # No local re-matching: every cluster the server returns is listed.
    for name in ("Alpha-Ray", "beta-ray", "gamma"):
        assert name in result.output


def test_raycluster_list_name_filter_is_local_and_labelled_cli_only(
    clusters, monkeypatch
):
    monkeypatch.setattr(raycluster_console, "width", 400)
    result, calls = _invoke_list(clusters, ["-n", "GAMMA", "-n", "alpha"])
    assert result.exit_code == 0, result.output
    assert calls == [{"q": None, "status": None, "created_by": None}]
    assert "gamma" in result.output
    assert "Alpha-Ray" in result.output
    assert "beta-ray" not in result.output

    help_result = CliRunner().invoke(raycluster, ["list", "--help"])
    assert help_result.exit_code == 0, help_result.output
    assert "CLI-only" in help_result.output
    assert "exact user ID or email" in help_result.output


def test_raycluster_list_reports_when_nothing_matches():
    result, calls = _invoke_list([], ["--search", "nothing"])
    assert result.exit_code == 0, result.output
    assert calls == [{"q": "nothing", "status": None, "created_by": None}]
    assert "No Ray clusters match the specified filters." in result.output


def test_raycluster_list_rejects_unknown_state(clusters):
    result, calls = _invoke_list(clusters, ["--state", "bogus"])
    assert result.exit_code == 2
    assert "Invalid value for '--state'" in result.output
    assert calls == []


def _invoke_list_jobs(jobs, args):
    calls = []

    def list_jobs(name):
        calls.append(name)
        return jobs

    fake_client = SimpleNamespace(raycluster=SimpleNamespace(list_jobs=list_jobs))
    with patch("leptonai.cli.raycluster.APIClient", return_value=fake_client):
        result = CliRunner().invoke(
            raycluster, ["list-jobs", "-n", "my-cluster", *args]
        )
    return result, calls


def test_raycluster_list_jobs_shows_and_filters_lepton_states(monkeypatch):
    monkeypatch.setattr(raycluster_console, "width", 240)
    jobs = [
        _ray_job("raysubmit_train", "Running", "python train.py"),
        _ray_job("raysubmit_eval", "Failed", "python eval.py"),
        _ray_job("raysubmit_wait", "Awaiting", "python wait.py"),
    ]

    listed, calls = _invoke_list_jobs(jobs, [])
    failed, _ = _invoke_list_jobs(jobs, ["--status", "failed"])
    awaiting, _ = _invoke_list_jobs(jobs, ["-s", "AWAITING"])
    no_match, _ = _invoke_list_jobs(jobs, ["-q", "train", "-s", "failed"])

    assert calls == ["my-cluster"]
    assert listed.exit_code == 0, listed.output
    # The Lepton state the dashboard shows, not the Ray-native status.
    for state in ("Running", "Failed", "Awaiting"):
        assert state in listed.output
    assert "PENDING" not in listed.output
    assert failed.exit_code == 0, failed.output
    assert "raysubmit_eval" in failed.output
    assert "raysubmit_train" not in failed.output
    assert awaiting.exit_code == 0, awaiting.output
    assert "raysubmit_wait" in awaiting.output
    assert "raysubmit_eval" not in awaiting.output
    assert no_match.exit_code == 0, no_match.output
    assert "No Ray jobs match the specified filters on this cluster." in no_match.output


def test_raycluster_list_jobs_rejects_ray_native_statuses():
    result, calls = _invoke_list_jobs([], ["--status", "SUCCEEDED"])
    assert result.exit_code == 2, result.output
    assert "'Completed'" in result.output
    assert calls == []


@responses.activate
def test_raycluster_list_jobs_reads_the_api_server_route(monkeypatch):
    monkeypatch.setattr(WorkspaceRecord, "_singleton_record", _LocalWorkspaceRecord())
    workspace_url = "https://gateway.example.com/api/v2/workspaces/ws1"
    client = APIClient(workspace_id="ws1", auth_token="token", url=workspace_url)
    monkeypatch.setattr("leptonai.cli.raycluster.APIClient", lambda: client)
    submission_client = Mock(wraps=JobSubmissionClient)
    monkeypatch.setattr(
        "leptonai.cli.raycluster.JobSubmissionClient", submission_client
    )
    responses.add(
        responses.GET,
        workspace_url + "/rayclusters/my-cluster/jobs",
        json=[{
            "metadata": {"id": "raysubmit_1", "name": "raysubmit_1"},
            "spec": {"entrypoint": "python train.py --ids [1,2]"},
            "status": {"state": "Completed", "message": "Job finished [ok]"},
        }],
    )
    responses.add(
        responses.GET,
        workspace_url + "/rayclusters/missing/jobs",
        status=404,
        json={"code": "ResourceNotFound", "message": "ray cluster missing not found"},
    )

    result = CliRunner().invoke(raycluster, ["list-jobs", "-n", "my-cluster"])
    missing = CliRunner().invoke(raycluster, ["list-jobs", "-n", "missing"])

    assert result.exit_code == 0, result.output or repr(result.exception)
    assert "raysubmit_1" in result.output
    assert "Completed" in result.output
    # Entrypoints and messages are printed verbatim, not as rich markup.
    assert "[1,2]" in result.output
    assert "[ok]" in result.output
    # The Ray dashboard proxy is no longer used for listing; the api-server
    # request identifies the CLI.
    submission_client.assert_not_called()
    assert all("/dashboard" not in call.request.url for call in responses.calls)
    assert responses.calls[0].request.headers["X-Lepton-Client"] == "cli"
    # A missing cluster still exits 1.
    assert missing.exit_code == 1
    assert "404" in missing.output


@pytest.mark.parametrize(
    "workspace_url, configured_origin, expected_origin",
    [
        (
            "https://gateway.dgxc-lepton.nvidia.com/api/v2/workspaces/ws1",
            None,
            "https://gateway.dgxc-lepton.nvidia.com",
        ),
        (
            "https://gateway.dgxc-lepton.nvidia.com/api/v2/workspaces/ws1",
            "https://console.example:8443/settings?source=cli#workspace",
            "https://console.example:8443",
        ),
        ("https://classic.example/api/v1", None, None),
    ],
    ids=["workspace-origin", "custom-origin", "classic-workspace"],
)
@pytest.mark.parametrize(
    "args, method, endpoint, payload",
    [
        (
            ["submit-job", "-n", "my-cluster", "--no-wait", "--", "echo", "hello"],
            "POST",
            "/api/jobs/",
            {"job_id": "raysubmit_test", "submission_id": "raysubmit_test"},
        ),
        (
            ["stop-job", "-n", "my-cluster", "-j", "raysubmit_test"],
            "POST",
            "/api/jobs/raysubmit_test/stop",
            {"stopped": True},
        ),
    ],
    ids=["submit-job", "stop-job"],
)
@responses.activate
def test_ray_job_requests_use_workspace_origin(
    monkeypatch,
    workspace_url,
    configured_origin,
    expected_origin,
    args,
    method,
    endpoint,
    payload,
):
    for name in (
        "LEPTON_WORKSPACE_ORIGIN_URL",
        "LEPTON_DEBUG_HEADERS",
        "RAY_ADDRESS",
        "RAY_API_SERVER_ADDRESS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(WorkspaceRecord, "_singleton_record", _LocalWorkspaceRecord())
    client = APIClient(
        workspace_id="ws1",
        auth_token="token",
        url=workspace_url,
        workspace_origin_url=configured_origin,
    )
    monkeypatch.setattr("leptonai.cli.raycluster.APIClient", lambda: client)
    submission_client = Mock(wraps=JobSubmissionClient)
    monkeypatch.setattr(
        "leptonai.cli.raycluster.JobSubmissionClient", submission_client
    )

    cluster_url = workspace_url + "/rayclusters/my-cluster"
    dashboard_url = cluster_url + "/dashboard"
    routes = {
        ("GET", cluster_url): _cluster("my-cluster").model_dump(
            mode="json", by_alias=True
        ),
        ("GET", dashboard_url + "/api/version"): {"ray_version": "2.49.2"},
        (method, dashboard_url + endpoint): payload,
    }

    def gateway_response(request):
        if request.headers.get("Origin") != expected_origin:
            return 403, {}, "Invalid origin"
        return (
            200,
            {"Content-Type": "application/json"},
            json.dumps(routes[request.method, request.url]),
        )

    for route_method, route_url in routes:
        responses.add_callback(route_method, route_url, callback=gateway_response)

    result = CliRunner().invoke(raycluster, args)

    assert result.exit_code == 0, result.output or repr(result.exception)
    if expected_origin is None:
        assert all(
            key.lower() != "origin"
            for key in submission_client.call_args.kwargs["headers"]
        )
    assert responses.calls[-1].request.method == method
    assert responses.calls[-1].request.url == dashboard_url + endpoint
    assert any(
        call.request.url == dashboard_url + "/api/version" for call in responses.calls
    )
    for call in responses.calls:
        assert call.request.headers.get("Origin") == expected_origin
        assert call.request.headers["Authorization"] == "Bearer token"
        assert call.request.headers["X-Lepton-Client"] == "cli"
