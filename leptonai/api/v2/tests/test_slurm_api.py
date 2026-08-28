from typing import Any
from unittest.mock import Mock

import pytest

from leptonai.api.v2.slurm import SlurmAPI


class _Response:
    def __init__(self, payload: Any, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = ""

    def json(self):
        return self._payload


def _api(response_payload: Any = None):
    client = Mock()
    response = _Response(response_payload)
    client._get.return_value = response
    client._post.return_value = response
    client._put.return_value = response
    client._patch.return_value = response
    client._delete.return_value = response
    client._head.return_value = response
    client.get_dashboard_base_url.return_value = (
        "https://dashboard.example.com/workspace/ws-1"
    )
    return SlurmAPI(client), client


def test_composite_cluster_id_and_dashboard_routes():
    api, _ = _api()

    assert api.split_cluster_id("namespace/cluster") == ("namespace", "cluster")
    assert api.dashboard_url("clusters").endswith("/clusters/slurm/list")
    assert api.dashboard_url("jobs").endswith("/compute/jobs/slurm-list")
    assert api.dashboard_url(
        "attempts", cluster_id="namespace/cluster", job_id="42"
    ).endswith("/clusters/slurm/detail/namespace%2Fcluster/jobs/detail/42/attempts")
    assert api.dashboard_url(
        "logs", cluster_id="namespace/cluster", job_id="42"
    ).endswith("#/slurm-cluster/namespace%2Fcluster/jobs/42/logs")

    with pytest.raises(ValueError, match="namespace/name"):
        api.split_cluster_id("cluster")


def test_cluster_list_exact_get_and_history_route():
    cluster = {
        "metadata": {"id": "ns/cluster-a", "name": "cluster-a"},
        "spec": {"workerClusterName": "worker-a"},
        "status": {"state": "Ready"},
    }
    api, client = _api([cluster])

    assert api.list_clusters()[0].status.state == "Ready"
    assert api.get_cluster("ns/cluster-a").spec.worker_cluster_name == "worker-a"

    client._get.reset_mock()
    client._get.return_value = _Response([{
        "timestamp": "2026-08-28T00:00:00Z",
        "type": "add_user",
        "user": "admin@example.com",
        "message": "Added user",
    }])
    events = api.list_cluster_events("ns/cluster-a", limit=20, event_type="add_user")

    assert events[0].type_ == "add_user"
    client._get.assert_called_once_with(
        "/slurmclusters/ns/cluster-a/history",
        params={"limit": 20, "event_type": "add_user"},
    )


def test_list_jobs_maps_workspace_filters_and_response():
    payload = {
        "page": 2,
        "page_size": 1,
        "total": 3,
        "failed_clusters": {"broken": "unavailable"},
        "jobs": [{
            "kind": "slurm",
            "slurm_cluster": {
                "id": "ns/cluster-a",
                "namespace_id": "ns",
                "cluster_id": "cluster-a",
                "name": "cluster-a",
            },
            "metadata": {
                "id": "42",
                "name": "train",
                "created_at": 1_700_000_000_000,
            },
            "spec": {"job_id": 42, "gpus": 8},
            "status": {"job_state": "RUNNING", "partition": "gpu"},
        }],
    }
    api, client = _api(payload)

    result = api.list_jobs(
        cluster_names=["ns/cluster-a"],
        job_query_mode="alive_and_archive",
        q="train",
        status=["RUNNING"],
        page=2,
        page_size=25,
        created_by=["user@example.com"],
        partition=["gpu"],
        qos=["normal"],
        sort_fields="job_id,created_at",
        sort_orders="desc,asc",
    )

    assert result.total == 3
    assert result.jobs[0].slurm_cluster.id_ == "ns/cluster-a"
    assert result.jobs[0].spec.gpus == 8
    client._get.assert_called_once_with(
        "/slurm/jobs",
        params={
            "job_query_mode": "alive_and_archive",
            "cluster_name": ["cluster-a"],
            "q": "train",
            "status": ["RUNNING"],
            "page": 2,
            "page_size": 25,
            "created_by": ["user@example.com"],
            "partition": ["gpu"],
            "qos": ["normal"],
            "sort_fields": "job_id,created_at",
            "sort_orders": "desc,asc",
        },
    )


def test_job_events_and_logs_use_cluster_scoped_parameters():
    event_payload = {
        "id": 42,
        "name": "train",
        "jobs": [{
            "attempt": 0,
            "state": "COMPLETED",
            "submit_at": 1_700_000_000_000,
            "steps": [{"id": "42.batch", "state": "COMPLETED"}],
        }],
    }
    api, client = _api(event_payload)

    client._get.return_value = _Response({
        "metadata": {"id": "42", "name": "train"},
        "spec": {"job_id": 42},
        "status": {"job_state": "RUNNING"},
    })
    job = api.get_job("ns/cluster a", "42_3")
    assert job.status.job_state == "RUNNING"
    client._get.assert_called_once_with(
        "/slurmclusters/ns/cluster%20a/jobs/42_3", params=None
    )

    client._get.reset_mock()
    client._get.return_value = _Response(event_payload)
    events = api.get_job_events("ns/cluster a", 42)

    assert events.jobs[0].steps[0].id_ == "42.batch"
    client._get.assert_called_once_with("/slurmclusters/ns/cluster%20a/jobs/42/events")

    client._get.reset_mock()
    client._get.return_value = _Response({"data": {"result": []}})
    api.get_logs(
        "ns/cluster a",
        job_id=42,
        attempt=0,
        step="42.batch",
        node="node-1",
        log_type="stderr.log",
        query="error",
        start=100,
        end=200,
        limit=50,
        direction="forward",
    )
    client._get.assert_called_once_with(
        "/logs",
        params={
            "slurm_namespace": "ns",
            "slurm_cluster": "cluster a",
            "limit": 50,
            "direction": "forward",
            "slurm_job": "42",
            "slurm_attempt": 0,
            "slurm_step": "42.batch",
            "slurm_node": "node-1",
            "slurm_log_type": "stderr.log",
            "q": "error",
            "start": 100,
            "end": 200,
        },
    )


def test_devpod_create_resolve_and_delete():
    created = {
        "metadata": {"id": "ns/cluster-a-alice", "name": "cluster-a-alice"},
        "spec": {"slurmClusterName": "cluster-a"},
        "status": {"state": "Ready", "sshCommand": "ssh alice@pod"},
    }
    api, client = _api(created)

    result = api.create_devpod("ns/cluster-a", set_name="gpu", cpu="4", memory="16Gi")

    assert result.status.ssh_command == "ssh alice@pod"
    client._post.assert_called_once_with(
        "/slurm/devpods",
        json={
            "spec": {
                "slurmClusterName": "cluster-a",
                "devPodSetName": "gpu",
                "resourceRequests": {"cpu": "4", "memory": "16Gi"},
            }
        },
    )

    client._get.return_value = _Response([created])
    assert api.resolve_devpod("ns/cluster-a").metadata.id_ == "ns/cluster-a-alice"

    client._delete.return_value = _Response({})
    assert api.delete_devpod("ns/cluster-a-alice") is True
    client._delete.assert_called_once_with("/slurm/devpods/ns/cluster-a-alice")
