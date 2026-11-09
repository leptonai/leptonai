"""HTTP contract tests for the RayClusterAPI list routes."""

import os
import tempfile
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

import pytest
import responses

from leptonai.api.v2.api_resource import ClientError
from leptonai.api.v2.client import APIClient

BASE = "https://gw.example/api/v2/workspaces/ws1"
RAYCLUSTERS = f"{BASE}/rayclusters"


def _client():
    return APIClient(workspace_id="ws1", auth_token="tok", url=BASE)


def _cluster(name, state="Ready"):
    return {
        "metadata": {"id": name, "name": name, "created_by": "alice@example.com"},
        "spec": {},
        "status": {"state": state},
    }


def _query(call):
    return parse_qs(urlparse(call.request.url).query)


@responses.activate
def test_list_all_without_filters_sends_the_plain_request():
    responses.add(responses.GET, RAYCLUSTERS, json=[_cluster("rc-a")])

    items = _client().raycluster.list_all()

    assert [item.metadata.name for item in items] == ["rc-a"]
    assert _query(responses.calls[0]) == {}


@responses.activate
def test_list_all_passes_the_dashboard_filters_to_the_server():
    responses.add(responses.GET, RAYCLUSTERS, json=[_cluster("rc-a", "Not Ready")])

    items = _client().raycluster.list_all(
        q="rc", status=["Not Ready", "Stopped"], created_by="alice@example.com"
    )

    assert items[0].status.state.value == "Not Ready"
    # Repeated keys, which the server reads with QueryArray; no pagination
    # parameters, so the server answers with the bare array.
    assert _query(responses.calls[0]) == {
        "q": ["rc"],
        "status": ["Not Ready", "Stopped"],
        "created_by": ["alice@example.com"],
    }


@responses.activate
def test_list_jobs_reads_the_api_server_route():
    responses.add(
        responses.GET,
        f"{RAYCLUSTERS}/my%20rc/jobs",
        json=[{
            "metadata": {"id": "raysubmit_1", "name": "raysubmit_1"},
            "spec": {
                "type": "SUBMISSION",
                "entrypoint": "python train.py",
                "job_id": "02000000",
                "submission_id": "raysubmit_1",
                "runtime_env": {"pip": ["torch"]},
            },
            "status": {
                "state": "Awaiting",
                "message": "waiting",
                "start_time": 1_700_000_000_000,
            },
        }],
    )

    jobs = _client().raycluster.list_jobs("my rc")

    assert len(jobs) == 1
    assert jobs[0].metadata.id_ == "raysubmit_1"
    assert jobs[0].spec.type_ == "SUBMISSION"
    assert jobs[0].spec.entrypoint == "python train.py"
    assert jobs[0].spec.runtime_env == {"pip": ["torch"]}
    # The Lepton state the server mapped the Ray status onto, kept verbatim.
    assert jobs[0].status.state == "Awaiting"
    assert jobs[0].status.start_time == 1_700_000_000_000


@responses.activate
def test_list_jobs_raises_on_a_missing_cluster():
    responses.add(
        responses.GET,
        f"{RAYCLUSTERS}/missing/jobs",
        status=404,
        json={"code": "ResourceNotFound", "message": "ray cluster missing not found"},
    )

    with pytest.raises(ClientError) as raised:
        _client().raycluster.list_jobs("missing")

    assert raised.value.response.status_code == 404
