from functools import partial
from types import SimpleNamespace
from unittest.mock import Mock, patch

from click.testing import CliRunner

from leptonai.api.v2.types.slurm import (
    LeptonSlurmCluster,
    LeptonSlurmDevPod,
    SlurmJob,
    SlurmJobEventList,
    WorkspaceSlurmJobList,
)
from leptonai.api.v2.slurm import SlurmAPI
from leptonai.cli import lep


CLUSTER = LeptonSlurmCluster(
    metadata={"id": "ns/cluster-a", "name": "cluster-a"},
    spec={
        "devPodsConfig": {
            "enabled": True,
            "bastion": {"enabled": True, "useLoadBalancer": True},
            "sets": [{"name": "gpu", "nodeGroupId": "ng-gpu"}],
        },
        "homeDirsConfig": {"storageBackend": {"hostPath": {"path": "/mnt/home"}}},
        "loginNodesConfig": {
            "nodeScratchPath": "/mnt/raid",
            "sourceCIDRs": ["10.0.0.0/8"],
        },
        "clusterSharedStorageConfig": {
            "sharedStoragePaths": [
                {"mountPath": "/shared", "readOnly": True},
                {
                    "mountPath": "/compute-only",
                    "excludedNodegroupTypes": ["login"],
                },
            ]
        },
    },
    status={
        "state": "Ready",
        "loginNodeAddresses": ["login.example.com"],
    },
)

DEVPOD = LeptonSlurmDevPod(
    metadata={
        "id": "ns/cluster-a-alice",
        "uuid": "devpod-uuid",
        "name": "cluster-a-alice",
        "created_at": 1_700_000_000,
        "created_by": "alice@example.com",
        "owner": "alice@example.com",
    },
    spec={"slurmClusterName": "cluster-a", "devPodSetName": "gpu"},
    status={
        "state": "Ready",
        "username": "alice",
        "imageVersion": "2026.09",
        "containerResources": {
            "requests": {"cpu": "4", "memory": "16Gi"},
            "limits": {"cpu": "8"},
        },
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
    # Cluster resolution runs the real SDK logic over list_clusters' return value.
    api.split_cluster_id.side_effect = SlurmAPI.split_cluster_id
    api.resolve_cluster.side_effect = partial(SlurmAPI.resolve_cluster, api)
    api.list_clusters.return_value = [CLUSTER]
    api.list_cluster_events.return_value = []
    api.list_jobs.return_value = JOBS
    api.list_cluster_jobs.return_value = []
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
    assert "dashboard" not in result.output
    assert "open" not in result.output.split()


def test_cluster_list_and_job_attempts_tables():
    client, api = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        clusters = CliRunner().invoke(lep, ["slurm", "cluster", "list"])
        attempts = CliRunner().invoke(
            lep,
            ["slurm", "job", "attempts", "-i", "42", "--steps"],
        )

    assert clusters.exit_code == 0, clusters.output
    assert "cluster-a" in clusters.output
    assert "login.example.com" in clusters.output
    assert attempts.exit_code == 0, attempts.output
    # The bare job ID resolves to its cluster through the jobs list.
    api.get_job_events.assert_called_once_with("ns/cluster-a", "42")
    assert "42.batch" in attempts.output
    # Raw Slurm states (COMPLETED) are normalized to CLI casing (Completed).
    assert "Completed" in attempts.output
    assert "COMPLETED" not in attempts.output


def test_cluster_list_filters_by_name_substring_and_exact_status():
    client, api = _fake_client()
    cluster_b = LeptonSlurmCluster(
        metadata={"id": "ns/cluster-beta", "name": "cluster-beta"},
        spec={},
        status={"state": "NotReady"},
    )
    prod = LeptonSlurmCluster(
        metadata={"id": "ns/prod-gpu", "name": "prod-gpu"},
        spec={},
        status={"state": "Error"},
    )
    api.list_clusters.return_value = [CLUSTER, cluster_b, prod]

    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        by_name = CliRunner().invoke(
            lep,
            ["slurm", "cluster", "list", "--name", "CLUSTER", "-o", "json"],
        )
        by_status = CliRunner().invoke(
            lep,
            ["slurm", "cluster", "list", "--status", "ready", "-o", "json"],
        )
        combined = CliRunner().invoke(
            lep,
            [
                "slurm",
                "cluster",
                "list",
                "-n",
                "cluster",
                "-n",
                "prod",
                "-s",
                "NotReady",
                "-s",
                "Error",
                "-o",
                "json",
            ],
        )

    assert by_name.exit_code == 0, by_name.output
    assert '"name": "cluster-a"' in by_name.output
    assert '"name": "cluster-beta"' in by_name.output
    assert '"name": "prod-gpu"' not in by_name.output

    assert by_status.exit_code == 0, by_status.output
    assert '"name": "cluster-a"' in by_status.output
    # Status matching is exact: Ready must not include NotReady.
    assert '"name": "cluster-beta"' not in by_status.output
    assert '"name": "prod-gpu"' not in by_status.output

    assert combined.exit_code == 0, combined.output
    assert '"name": "cluster-beta"' in combined.output
    assert '"name": "cluster-a"' not in combined.output
    assert '"name": "prod-gpu"' in combined.output
    assert api.list_clusters.call_count == 3


def test_cluster_list_repeated_name_filters_are_or_conditions():
    client, api = _fake_client()
    prod = LeptonSlurmCluster(
        metadata={"id": "ns/prod-gpu", "name": "prod-gpu"},
        spec={},
        status={"state": "Error"},
    )
    api.list_clusters.return_value = [CLUSTER, prod]

    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        result = CliRunner().invoke(
            lep,
            [
                "slurm",
                "cluster",
                "list",
                "-n",
                "cluster-a",
                "-n",
                "PROD",
                "-o",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    assert '"name": "cluster-a"' in result.output
    assert '"name": "prod-gpu"' in result.output


def test_state_cells_are_normalized_and_colorized():
    from leptonai.cli.slurm import _normalize_state, _state_cell

    assert _normalize_state("RUNNING") == "Running"
    assert _normalize_state("NODE_FAIL") == "NodeFail"
    assert _normalize_state("Queueing") == "Queueing"
    assert _normalize_state(None) == "-"

    assert _state_cell("RUNNING") == "[green]Running[/]"
    assert _state_cell("FAILED") == "[red]Failed[/]"
    assert _state_cell("NODE_FAIL") == "[red]NodeFail[/]"
    assert _state_cell("Unrecoverable") == "[red]Unrecoverable[/]"
    assert _state_cell("PENDING") == "[yellow]Pending[/]"
    # The first non-empty candidate wins (job_state preferred over state).
    assert _state_cell(None, "Running") == "[green]Running[/]"
    assert _state_cell(None, None) == "-"


def test_job_list_table_links_to_dashboard_and_normalizes_state():
    client, api = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        result = CliRunner().invoke(lep, ["slurm", "job", "list"])

    assert result.exit_code == 0, result.output
    assert "train" in result.output
    assert "RUNNING" not in result.output
    api.dashboard_url.assert_any_call(
        "overview", cluster_id="ns/cluster-a", job_id="42"
    )


def test_job_list_exposes_only_supported_filter_options():
    result = CliRunner().invoke(lep, ["slurm", "job", "list", "--help"])

    assert result.exit_code == 0, result.output
    assert "--status" in result.output
    for unsupported in (
        "--page",
        "--page-size",
        "--partition",
        "--qos",
        "--sort-by",
        "--order",
    ):
        assert unsupported not in result.output


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
                "--status",
                "RUNNING",
                "--status",
                "FAILED",
                "--include-archived",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    assert '"job_id": 42' in result.output
    api.list_jobs.assert_called_once_with(
        cluster_names=["ns/cluster-a"],
        job_query_mode="alive_and_archive",
        q=None,
        status=["RUNNING", "FAILED"],
        created_by=None,
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
                "-i",
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


def _job_entry(job_id, name, cluster_id, state="Running"):
    return {
        "kind": "slurm",
        "slurm_cluster": {"id": cluster_id, "name": cluster_id.split("/")[1]},
        "metadata": {
            "id": str(job_id),
            "name": name,
            "created_at": 1_700_000_000_000,
        },
        "spec": {"job_id": job_id, "cpus": 1, "gpus": 0, "memory_mb": 1024},
        "status": {"state": state, "job_state": state.upper()},
    }


AMBIGUOUS_JOBS = WorkspaceSlurmJobList(
    page=1,
    page_size=2,
    total=2,
    jobs=[
        _job_entry(42, "train", "ns-a/cluster-a"),
        _job_entry(7, "train", "ns-b/cluster-b"),
    ],
)

EMPTY_JOBS = WorkspaceSlurmJobList(page=1, page_size=0, total=0, jobs=[])


def test_job_attempts_with_cluster_and_id_skips_job_listing():
    client, api = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        # The cluster is accepted as NAMESPACE/NAME or bare NAME; both are
        # validated against list_clusters before any job lookup.
        full = CliRunner().invoke(
            lep,
            ["slurm", "job", "attempts", "-i", "42", "--cluster", "ns/cluster-a"],
        )
        bare = CliRunner().invoke(
            lep,
            ["slurm", "job", "attempts", "-i", "42", "--cluster", "cluster-a"],
        )

    assert full.exit_code == 0, full.output
    assert bare.exit_code == 0, bare.output
    api.list_jobs.assert_not_called()
    api.list_cluster_jobs.assert_not_called()
    assert api.get_job_events.call_count == 2
    api.get_job_events.assert_called_with("ns/cluster-a", "42")


def test_job_commands_error_on_unknown_cluster():
    client, api = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        attempts = CliRunner().invoke(
            lep,
            ["slurm", "job", "attempts", "-i", "42", "--cluster", "nope"],
        )
        listing = CliRunner().invoke(lep, ["slurm", "job", "list", "--cluster", "nope"])

    assert attempts.exit_code == 1, attempts.output
    assert "was not found" in attempts.output
    assert "ns/cluster-a" in attempts.output
    api.get_job_events.assert_not_called()
    assert listing.exit_code == 1, listing.output
    api.list_jobs.assert_not_called()


def test_job_attempts_errors_on_ambiguous_name():
    client, api = _fake_client()
    api.list_jobs.return_value = AMBIGUOUS_JOBS
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        result = CliRunner().invoke(lep, ["slurm", "job", "attempts", "-n", "train"])

    assert result.exit_code == 1, result.output
    assert "ns-a/cluster-a" in result.output
    assert "ns-b/cluster-b" in result.output
    api.get_job_events.assert_not_called()


def test_job_attempts_name_resolved_inside_selected_cluster():
    client, api = _fake_client()
    cluster_b = LeptonSlurmCluster(
        metadata={"id": "ns-b/cluster-b", "name": "cluster-b"},
        spec={},
        status={"state": "Ready", "loginNodeAddresses": []},
    )
    api.list_clusters.return_value = [CLUSTER, cluster_b]
    api.list_cluster_jobs.return_value = [
        SlurmJob(
            metadata={"id": "7", "name": "train"},
            spec={"job_id": 7},
            status={"state": "Running", "job_state": "RUNNING"},
        )
    ]
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        result = CliRunner().invoke(
            lep,
            ["slurm", "job", "attempts", "-n", "train", "--cluster", "cluster-b"],
        )

    assert result.exit_code == 0, result.output
    # A validated cluster routes the search to the cluster-scoped jobs API.
    api.list_jobs.assert_not_called()
    assert api.list_cluster_jobs.call_args.args == ("ns-b/cluster-b",)
    assert api.list_cluster_jobs.call_args.kwargs["q"] == "train"
    api.get_job_events.assert_called_once_with("ns-b/cluster-b", "7")


def test_job_get_prints_all_jobs_sharing_a_name():
    client, api = _fake_client()
    api.list_jobs.return_value = AMBIGUOUS_JOBS
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        result = CliRunner().invoke(lep, ["slurm", "job", "get", "-n", "train"])

    assert result.exit_code == 0, result.output
    assert api.get_job.call_count == 2
    assert result.output.lstrip().startswith("[")


def test_job_selector_requires_exactly_one_of_name_or_id():
    client, api = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        neither = CliRunner().invoke(lep, ["slurm", "job", "attempts"])
        both = CliRunner().invoke(
            lep, ["slurm", "job", "get", "-n", "train", "-i", "42"]
        )

    assert neither.exit_code == 2, neither.output
    assert "either --name or --id" in neither.output
    assert both.exit_code == 2, both.output
    assert "only one" in both.output
    api.list_jobs.assert_not_called()


def test_job_resolution_zero_match_hints_archived():
    client, api = _fake_client()
    api.list_jobs.return_value = EMPTY_JOBS
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        default = CliRunner().invoke(lep, ["slurm", "job", "attempts", "-i", "99"])
        archived = CliRunner().invoke(
            lep, ["slurm", "job", "attempts", "-i", "99", "--include-archived"]
        )

    assert default.exit_code == 1, default.output
    assert "--include-archived" in default.output
    assert default.output.count("--include-archived") == 1
    assert archived.exit_code == 1, archived.output
    assert "--include-archived" not in archived.output
    assert api.list_jobs.call_args.kwargs["job_query_mode"] == "alive_and_archive"


def test_devpod_create_remove_and_safe_ssh_print():
    client, api = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        created = CliRunner().invoke(
            lep,
            [
                "slurm",
                "devpod",
                "create",
                "--cluster",
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
            lep, ["slurm", "devpod", "remove", "--cluster", "cluster-a", "--yes"]
        )
        ssh = CliRunner().invoke(
            lep,
            [
                "slurm",
                "devpod",
                "ssh",
                "--name",
                "cluster-a-alice",
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
    api.resolve_devpod.assert_any_call(None, cluster="ns/cluster-a")
    api.resolve_devpod.assert_any_call("cluster-a-alice")


def test_devpod_get_shows_configuration_identity_and_connect_details():
    client, api = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        result = CliRunner().invoke(
            lep, ["slurm", "devpod", "get", "--name", "cluster-a-alice"]
        )

    assert result.exit_code == 0, result.output
    for expected in (
        "Configuration",
        "Environment profile",
        "gpu",
        "Profile node group",
        "ng-gpu",
        "CPU request",
        "4",
        "Memory request",
        "16Gi",
        "CPU limit",
        "8",
        "No limit",
        "Bastion",
        "Enabled",
        "/home",
        "/mnt/home",
        "/raid",
        "/shared",
        "Identity",
        "Cluster user",
        "alice",
        "devpod-uuid",
        "alice@example.com",
        "Connect",
        "SSH via bastion",
        "ssh -J alice@bastion alice@pod",
        "Open in web UI",
    ):
        assert expected in result.output
    assert "/compute-only" not in result.output
    api.list_clusters.assert_called_once_with()
    api.dashboard_url.assert_called_once_with("devpods", cluster_id="ns/cluster-a")


def test_devpod_get_json_preserves_raw_record_without_cluster_lookup():
    client, api = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        result = CliRunner().invoke(
            lep,
            [
                "slurm",
                "devpod",
                "get",
                "--id",
                "ns/cluster-a-alice",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == 0, result.output
    assert '"uuid": "devpod-uuid"' in result.output
    assert '"sshCommand": "ssh -J alice@bastion alice@pod"' in result.output
    api.list_clusters.assert_not_called()


def test_devpod_list_links_name_id_cell_to_web_ui():
    client, api = _fake_client()
    with (
        patch("leptonai.cli.slurm.APIClient", return_value=client),
        patch(
            "leptonai.cli.slurm.make_name_id_cell", return_value="linked-name-id"
        ) as name_id_cell,
    ):
        result = CliRunner().invoke(lep, ["slurm", "devpod", "list"])

    assert result.exit_code == 0, result.output
    api.dashboard_url.assert_called_once_with("devpods", cluster_id="ns/cluster-a")
    api.list_clusters.assert_called_once_with()
    name_id_cell.assert_called_once_with(
        "cluster-a-alice",
        "ns/cluster-a-alice",
        link=api.dashboard_url.return_value,
    )


def test_devpod_ssh_runs_bastion_command_with_extra_options_before_destination():
    client, _ = _fake_client()
    with (
        patch("leptonai.cli.slurm.APIClient", return_value=client),
        patch(
            "leptonai.cli.slurm.subprocess.run",
            return_value=SimpleNamespace(returncode=0),
        ) as run,
    ):
        result = CliRunner().invoke(
            lep,
            [
                "slurm",
                "devpod",
                "ssh",
                "--id",
                "ns/cluster-a-alice",
                "--",
                "-v",
            ],
        )

    assert result.exit_code == 0, result.output
    run.assert_called_once_with(
        ["ssh", "-v", "-J", "alice@bastion", "alice@pod"], check=False
    )


def test_devpod_ssh_fails_closed_when_bastion_is_disabled():
    disabled_cluster = LeptonSlurmCluster(
        metadata={"id": "ns/cluster-a", "name": "cluster-a"},
        spec={"devPodsConfig": {"enabled": True, "bastion": {"enabled": False}}},
        status={"state": "Ready"},
    )
    client, api = _fake_client()
    api.list_clusters.return_value = [disabled_cluster]
    with (
        patch("leptonai.cli.slurm.APIClient", return_value=client),
        patch("leptonai.cli.slurm.subprocess.run") as run,
    ):
        result = CliRunner().invoke(
            lep,
            [
                "slurm",
                "devpod",
                "ssh",
                "--id",
                "ns/cluster-a-alice",
            ],
        )

    assert result.exit_code == 1, result.output
    assert "SSH via bastion is not enabled" in result.output
    run.assert_not_called()


def test_devpod_create_resolves_bare_cluster_name():
    client, api = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        created = CliRunner().invoke(
            lep, ["slurm", "devpod", "create", "-c", "cluster-a"]
        )
        unknown = CliRunner().invoke(lep, ["slurm", "devpod", "create", "-c", "nope"])

    assert created.exit_code == 0, created.output
    # The bare NAME is validated against list_clusters and expanded to the
    # canonical NAMESPACE/NAME ID before the create call.
    api.create_devpod.assert_called_once_with(
        "ns/cluster-a", set_name=None, cpu=None, memory=None
    )
    assert unknown.exit_code == 1, unknown.output
    assert "was not found" in unknown.output
    assert api.create_devpod.call_count == 1


def test_devpod_selector_allows_cluster_to_scope_name_or_id():
    client, api = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        neither = CliRunner().invoke(lep, ["slurm", "devpod", "get"])
        name_and_id = CliRunner().invoke(
            lep,
            [
                "slurm",
                "devpod",
                "get",
                "-n",
                "cluster-a-alice",
                "-i",
                "ns/cluster-a-alice",
                "-c",
                "cluster-a",
            ],
        )
        scoped = CliRunner().invoke(
            lep,
            [
                "slurm",
                "devpod",
                "get",
                "-n",
                "cluster-a-alice",
                "-c",
                "cluster-a",
                "-o",
                "json",
            ],
        )

    assert neither.exit_code == 2, neither.output
    assert "one of --name, --id, or --cluster" in neither.output
    assert name_and_id.exit_code == 2, name_and_id.output
    assert "cannot provide both --name and --id" in name_and_id.output
    assert scoped.exit_code == 0, scoped.output
    api.resolve_devpod.assert_called_once_with(
        "cluster-a-alice", cluster="ns/cluster-a"
    )


def test_cluster_get_and_events_resolve_name_or_id():
    client, api = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        by_name = CliRunner().invoke(
            lep, ["slurm", "cluster", "get", "-n", "cluster-a"]
        )
        events = CliRunner().invoke(
            lep,
            ["slurm", "cluster", "events", "-i", "ns/cluster-a", "--limit", "5"],
        )
        unknown = CliRunner().invoke(lep, ["slurm", "cluster", "get", "-n", "nope"])
        neither = CliRunner().invoke(lep, ["slurm", "cluster", "get"])

    assert by_name.exit_code == 0, by_name.output
    assert '"id": "ns/cluster-a"' in by_name.output
    assert events.exit_code == 0, events.output
    api.list_cluster_events.assert_called_once_with(
        "ns/cluster-a", limit=5, event_type=None
    )
    assert unknown.exit_code == 1, unknown.output
    assert "was not found" in unknown.output
    assert neither.exit_code == 2, neither.output
    assert "either --name or --id" in neither.output


def test_slurm_commands_reject_positional_arguments():
    client, _ = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        for args in (
            ["slurm", "cluster", "get", "ns/cluster-a"],
            ["slurm", "cluster", "events", "ns/cluster-a"],
            ["slurm", "devpod", "get", "ns/cluster-a"],
            ["slurm", "devpod", "create", "ns/cluster-a"],
            ["slurm", "devpod", "remove", "ns/cluster-a", "--yes"],
        ):
            result = CliRunner().invoke(lep, args)
            assert result.exit_code == 2, (args, result.output)


def test_open_and_dashboard_commands_are_removed():
    for args in (
        ["slurm", "dashboard"],
        ["slurm", "open"],
        ["slurm", "cluster", "open", "ns/cluster-a"],
        ["slurm", "job", "open", "ns/cluster-a", "42"],
        ["slurm", "devpod", "open", "ns/cluster-a"],
    ):
        result = CliRunner().invoke(lep, args)
        assert result.exit_code != 0, args


def test_devpod_bastion_ssh_and_shell_are_in_command_tree():
    cluster_help = CliRunner().invoke(lep, ["slurm", "cluster", "--help"])
    devpod_help = CliRunner().invoke(lep, ["slurm", "devpod", "--help"])

    assert "shell" in cluster_help.output
    assert "ssh" not in cluster_help.output
    assert "shell" in devpod_help.output
    assert "ssh" in devpod_help.output
    result = CliRunner().invoke(lep, ["slurm", "cluster", "ssh", "-n", "cluster-a"])
    assert result.exit_code == 2, result.output
    assert "No such command" in result.output


def test_shell_requires_interactive_terminal():
    client, api = _fake_client()
    # CliRunner feeds pipes, not TTYs, so the guard must trip before any
    # network traffic happens.
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        cluster = CliRunner().invoke(
            lep, ["slurm", "cluster", "shell", "-n", "cluster-a"]
        )
        devpod = CliRunner().invoke(
            lep, ["slurm", "devpod", "shell", "-n", "cluster-a-alice"]
        )

    assert cluster.exit_code == 2, cluster.output
    assert "requires a terminal" in cluster.output
    assert devpod.exit_code == 2, devpod.output
    api.shell_connection.assert_not_called()
    api.devpod_shell_connection.assert_not_called()
    api.resolve_devpod.assert_not_called()


def test_cluster_shell_bridges_the_websocket():
    client, api = _fake_client()
    socket = object()
    api.shell_connection.return_value = socket
    with (
        patch("leptonai.cli.slurm.APIClient", return_value=client),
        patch("leptonai.cli.ws_shell.ensure_interactive_terminal"),
        patch("leptonai.cli.ws_shell.run_ws_shell", return_value=0) as bridge,
    ):
        result = CliRunner().invoke(
            lep, ["slurm", "cluster", "shell", "-n", "cluster-a"]
        )

    assert result.exit_code == 0, result.output
    api.shell_connection.assert_called_once_with("ns/cluster-a")
    bridge.assert_called_once_with(socket)


def test_devpod_shell_bridges_and_propagates_exit_code():
    client, api = _fake_client()
    socket = object()
    api.devpod_shell_connection.return_value = socket
    with (
        patch("leptonai.cli.slurm.APIClient", return_value=client),
        patch("leptonai.cli.ws_shell.ensure_interactive_terminal"),
        patch("leptonai.cli.ws_shell.run_ws_shell", return_value=130) as bridge,
    ):
        result = CliRunner().invoke(
            lep, ["slurm", "devpod", "shell", "-n", "cluster-a-alice"]
        )

    assert result.exit_code == 130, result.output
    api.resolve_devpod.assert_called_once_with("cluster-a-alice")
    api.devpod_shell_connection.assert_called_once_with("ns/cluster-a-alice")
    bridge.assert_called_once_with(socket)


def test_job_logs_follow_seeds_newest_page_then_drains_full_pages():
    client, api = _fake_client()

    def page(first, count):
        values = [[str(first + i), f"line-{first + i}"] for i in range(count)]
        return {"data": {"result": [{"values": values}]}}

    api.get_logs.side_effect = [
        page(1_000, 2),  # backward seed: the newest lines in the window
        page(2_000, 3),  # forward: a full page, so the next poll is immediate
        page(3_000, 1),  # forward: a short page, so the loop sleeps
        KeyboardInterrupt(),
    ]
    with (
        patch("leptonai.cli.slurm.APIClient", return_value=client),
        patch("leptonai.cli.slurm.time.sleep") as sleep,
    ):
        result = CliRunner().invoke(
            lep, ["slurm", "job", "logs", "-i", "42", "--follow", "--limit", "3"]
        )

    assert result.exit_code == 0, result.output
    calls = api.get_logs.call_args_list
    assert [call.kwargs["direction"] for call in calls] == [
        "backward",
        "forward",
        "forward",
        "forward",
    ]
    # Every forward poll resumes right after the newest timestamp seen so far.
    assert [call.kwargs["start"] for call in calls[1:]] == [1_002, 2_003, 3_001]
    assert sleep.call_count == 1
    assert result.output.index("line-1000") < result.output.index("line-3000")
    assert "Stopped following" in result.output


def test_devpod_list_validates_cluster_filter():
    client, api = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        unknown = CliRunner().invoke(lep, ["slurm", "devpod", "list", "-c", "nope"])
        known = CliRunner().invoke(
            lep, ["slurm", "devpod", "list", "-c", "cluster-a", "-o", "json"]
        )

    assert unknown.exit_code == 1, unknown.output
    assert "was not found" in unknown.output
    assert known.exit_code == 0, known.output
    # The unknown name never reaches the API; the known one is canonicalized.
    api.list_devpods.assert_called_once_with(cluster_names=["ns/cluster-a"])


def test_devpod_cluster_scope_lists_clusters_once():
    client, api = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        shown = CliRunner().invoke(lep, ["slurm", "devpod", "get", "-c", "cluster-a"])

    assert shown.exit_code == 0, shown.output
    assert "Configuration" in shown.output
    api.resolve_devpod.assert_called_once_with(None, cluster="ns/cluster-a")
    api.list_clusters.assert_called_once_with()

    client, api = _fake_client()
    with patch("leptonai.cli.slurm.APIClient", return_value=client):
        ssh = CliRunner().invoke(
            lep, ["slurm", "devpod", "ssh", "-c", "cluster-a", "--print-only"]
        )

    assert ssh.exit_code == 0, ssh.output
    api.list_clusters.assert_called_once_with()
