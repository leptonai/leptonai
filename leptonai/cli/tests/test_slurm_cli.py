from types import SimpleNamespace
from unittest.mock import Mock, patch

from click.testing import CliRunner

from leptonai.api.v2.types.slurm import (
    LeptonSlurmCluster,
    LeptonSlurmDevPod,
    SlurmJobEventList,
    WorkspaceSlurmJobList,
)
from leptonai.cli import lep


CLUSTER = LeptonSlurmCluster(
    metadata={"id": "ns/cluster-a", "name": "cluster-a"},
    spec={"devPodsConfig": {"enabled": True}},
    status={
        "state": "Ready",
        "loginNodeAddresses": ["login.example.com"],
    },
)

DEVPOD = LeptonSlurmDevPod(
    metadata={"id": "ns/cluster-a-alice", "name": "cluster-a-alice"},
    spec={"slurmClusterName": "cluster-a"},
    status={
        "state": "Ready",
        "username": "alice",
        "sshCommand": "ssh -J alice@bastion alice@pod",
    },
)

JOBS = WorkspaceSlurmJobList(
    page=1,
    page_size=1,
    total=1,
    jobs=[{
        "kind": "slurm",
        "slurm_cluster": {"id": "ns/cluster-a", "name": "cluster-a"},
        "metadata": {
            "id": "42",
            "name": "train",
            "created_by": "alice@example.com",
            "created_at": 1_700_000_000_000,
        },
        "spec": {"job_id": 42, "cpus": 8, "gpus": 1, "memory_mb": 4096},
        "status": {
            "state": "Running",
            "job_state": "RUNNING",
            "partition": "gpu",
            "qos": "normal",
        },
    }],
)

EVENTS = SlurmJobEventList(
    id=42,
    name="train",
    jobs=[{
        "attempt": 0,
        "state": "COMPLETED",
        "start_at": 1_700_000_000_000,
        "end_at": 1_700_000_005_000,
        "steps": [{"id": "42.batch", "state": "COMPLETED"}],
    }],
)


def _fake_client():
    api = Mock()
    api.list_clusters.return_value = [CLUSTER]
    api.get_cluster.return_value = CLUSTER
    api.list_cluster_events.return_value = []
    api.list_jobs.return_value = JOBS
    api.get_job.return_value = JOBS.jobs[0]
    api.get_job_events.return_value = EVENTS
    api.get_logs.return_value = {
        "data": {
            "result": [
                {"values": [["1700000001000000000", "second"]]},
                {"values": [["1700000000000000000", "first"]]},
            ]
        }
    }
    api.list_devpods.return_value = [DEVPOD]
    api.resolve_devpod.return_value = DEVPOD
    api.create_devpod.return_value = DEVPOD
    api.delete_devpod.return_value = True
    api.dashboard_url.return_value = (
        "https://dashboard.example.com/workspace/ws-1/clusters/slurm/list"
    )
    return SimpleNamespace(slurm=api), api


def test_slurm_command_tree_is_registered():
    result = CliRunner().invoke(lep, ["slurm", "--help"])

    assert result.exit_code == 0, result.output
    assert "cluster" in result.output
    assert "job" in result.output
    assert "devpod" in result.output
    assert "dashboard" in result.output


def test_cluster_list_and_job_attempts_tables():
    client, _ = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        clusters = CliRunner().invoke(lep, ["slurm", "cluster", "list"])
        attempts = CliRunner().invoke(
            lep,
            ["slurm", "job", "attempts", "ns/cluster-a", "42", "--steps"],
        )

    assert clusters.exit_code == 0, clusters.output
    assert "cluster-a" in clusters.output
    assert "login.example.com" in clusters.output
    assert attempts.exit_code == 0, attempts.output
    assert "42.batch" in attempts.output
    assert "COMPLETED" in attempts.output


def test_job_list_passes_workspace_filters_and_archive_mode():
    client, api = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        result = CliRunner().invoke(
            lep,
            [
                "slurm",
                "job",
                "list",
                "--cluster",
                "ns/cluster-a",
                "--state",
                "RUNNING",
                "--archived",
                "--partition",
                "gpu",
                "--sort-by",
                "job_id",
                "--order",
                "desc",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    assert '"job_id": 42' in result.output
    api.list_jobs.assert_called_once_with(
        cluster_names=["ns/cluster-a"],
        job_query_mode="archive_only",
        q=None,
        status=["RUNNING"],
        page=None,
        page_size=None,
        created_by=None,
        partition=["gpu"],
        qos=None,
        sort_fields="job_id",
        sort_orders="desc",
    )


def test_job_logs_maps_scope_and_prints_in_timestamp_order():
    client, api = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        result = CliRunner().invoke(
            lep,
            [
                "slurm",
                "job",
                "logs",
                "ns/cluster-a",
                "42",
                "--attempt",
                "0",
                "--step",
                "42.batch",
                "--log-type",
                "stderr",
            ],
        )

    assert result.exit_code == 0, result.output
    assert result.output.index("first") < result.output.index("second")
    api.get_logs.assert_called_once_with(
        "ns/cluster-a",
        start=None,
        end=None,
        direction="backward",
        job_id="42",
        attempt=0,
        step="42.batch",
        node=None,
        log_type="stderr.log",
        query=None,
        limit=100,
    )


def test_devpod_create_remove_and_safe_ssh_print():
    client, api = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        created = CliRunner().invoke(
            lep,
            [
                "slurm",
                "devpod",
                "create",
                "ns/cluster-a",
                "--set",
                "gpu",
                "--cpu",
                "4",
                "--memory",
                "16Gi",
            ],
        )
        removed = CliRunner().invoke(
            lep, ["slurm", "devpod", "remove", "ns/cluster-a", "--yes"]
        )
        ssh = CliRunner().invoke(
            lep,
            [
                "slurm",
                "devpod",
                "ssh",
                "ns/cluster-a",
                "--print-only",
            ],
        )

    assert created.exit_code == 0, created.output
    api.create_devpod.assert_called_once_with(
        "ns/cluster-a", set_name="gpu", cpu="4", memory="16Gi"
    )
    assert removed.exit_code == 0, removed.output
    api.delete_devpod.assert_called_once_with("ns/cluster-a-alice")
    assert ssh.exit_code == 0, ssh.output
    assert "ssh -J alice@bastion alice@pod" in ssh.output


def test_dashboard_print_only_uses_canonical_url_builder():
    client, api = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        result = CliRunner().invoke(
            lep, ["slurm", "job", "open", "ns/cluster-a", "42", "--print-only"]
        )

    assert result.exit_code == 0, result.output
    assert "https://dashboard.example.com" in result.output
    api.dashboard_url.assert_called_once_with(
        "overview", cluster_id="ns/cluster-a", job_id="42"
    )
