"""Slurm login, job and Dev Pod Teleport SSH without live credentials."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import subprocess
from unittest.mock import patch

import pytest
import responses
from click.testing import CliRunner

from leptonai.api.v2.client import APIClient
from leptonai.cli import lep


BASE = "https://gw.example/api/v2/workspaces/ws-slurm"
TOKEN = "nvapi-" + "a" * 40
CLUSTERS_URL = f"{BASE}/slurmclusters"
JOBS_URL = f"{BASE}/slurmclusters/slurm/training/jobs"
DEVPOD_URL = f"{BASE}/slurm/devpods/slurm-training/training-alice"
CLUSTER = {
    "metadata": {"id": "slurm/training", "name": "training", "uuid": "cluster-1"},
    "spec": {
        "loginNodesConfig": {"enableTeleport": True},
        "gpuNodeGroupsConfig": {
            "groups": [{"id": "gpu-group", "enableTeleport": True}]
        },
        "ldapConfig": {"domainSuffix": {"example.com": "_corp"}},
    },
    "status": {
        "state": "Ready",
        "teleportCluster": "proxy.example.com",
        "loginNodeNames": ["login-1", "login-0"],
    },
}
JOB = {
    "metadata": {"id": "42", "owner": "alice_corp", "created_at": 1_700_000_000},
    "spec": {"job_id": 42},
    "status": {"state": "Running", "job_state": "RUNNING", "nodes": ["gpu-1"]},
}
DEVPOD = {
    "metadata": {
        "id": "slurm-training/training-alice",
        "name": "training-alice",
        "uuid": "devpod-1",
        "created_at": 1_700_000_000,
        "owner": "alice@example.com",
    },
    "spec": {"slurmClusterName": "training"},
    "status": {
        "state": "Ready",
        "podName": "training-alice",
        "teleportNodeName": "training-alice",
        "teleportCluster": "proxy.example.com",
        "username": "alice",
    },
}


def completed(stdout="", code=0):
    return subprocess.CompletedProcess([], code, stdout, "")


def profile(logins=("alice_corp",)):
    return completed(
        json.dumps({
            "active": {
                "profile_url": "https://proxy.example.com:443",
                "cluster": "teleport-root.example.com",
                "username": "alice@example.com",
                "valid_until": (
                    datetime.now(timezone.utc) + timedelta(hours=1)
                ).isoformat(),
                "logins": list(logins),
            }
        })
    )


def inventory(hostname, host_id="host-uuid-1"):
    return completed(
        json.dumps([{
            "kind": "node",
            "metadata": {
                "name": host_id,
                "labels": {
                    "teleport.lepton.ai/slurm-cluster": "training",
                    "cluster": "training",
                    "hostname": hostname,
                },
            },
            "spec": {"hostname": hostname},
        }])
    )


@pytest.fixture
def session():
    client = APIClient(workspace_id="ws-slurm", auth_token=TOKEN, url=BASE)
    with (
        responses.RequestsMock(assert_all_requests_are_fired=False) as http,
        patch("leptonai.cli.slurm.APIClient", return_value=client),
        patch("leptonai.cli.teleport._require_tsh", return_value="/usr/bin/tsh"),
        patch("leptonai.cli.teleport.subprocess.run") as run,
    ):
        http.get(BASE, json={"name": "ws-slurm", "role": "user"})
        http.get(
            f"{BASE}/tokens",
            json=[{
                "masked_value": "nvapi-aaaaaa...aaaaaa",
                "created_by": "alice@example.com",
            }],
        )
        http.get(CLUSTERS_URL, json=[CLUSTER])
        http.get(JOBS_URL, json={"jobs": [JOB], "total": 1})
        http.get(DEVPOD_URL, json=DEVPOD)
        http.get(f"{BASE}/slurm/devpods", json=[DEVPOD])
        yield http, run


def invoke(*args):
    return CliRunner().invoke(lep, ["slurm", *args])


def ssh_args(run):
    return run.call_args.args[0]


def with_cluster(http, **changes):
    cluster = deepcopy(CLUSTER)
    for path, value in changes.items():
        parent = cluster
        keys = path.split("__")
        for key in keys[:-1]:
            parent = parent.setdefault(key, {})
        if value is None:
            parent.pop(keys[-1], None)
        else:
            parent[keys[-1]] = value
    http.replace(responses.GET, CLUSTERS_URL, json=[cluster])


# --- login nodes ---------------------------------------------------------


def test_login_ssh_uses_the_first_login_node_and_mapped_account(session):
    http, run = session
    run.side_effect = [profile(), inventory("login-0"), completed()]
    result = invoke("cluster", "ssh", "-n", "training")
    assert result.exit_code == 0, result.output
    assert "Connecting to Slurm login node login-0 as alice_corp" in result.output
    listing = run.call_args_list[1].args[0]
    assert listing[-1] == "teleport.lepton.ai/slurm-cluster=training,cluster=training"
    assert ssh_args(run) == [
        "/usr/bin/tsh",
        "ssh",
        "--proxy=proxy.example.com:443",
        "--cluster=teleport-root.example.com",
        "--user=alice@example.com",
        "alice_corp@host-uuid-1",
    ]


def test_login_ssh_connects_to_a_named_login_node(session):
    http, run = session
    run.side_effect = [profile(), inventory("login-1", "host-uuid-2"), completed()]
    result = invoke("cluster", "ssh", "--id", "slurm/training", "--node", "login-1")
    assert result.exit_code == 0, result.output
    assert ssh_args(run)[-1] == "alice_corp@host-uuid-2"


def test_login_ssh_states_the_allowed_group_policy(session):
    http, run = session
    with_cluster(http, spec__loginNodesConfig__allowGroups=["hpc-users"])
    run.side_effect = [profile(), inventory("login-0"), completed()]
    result = invoke("cluster", "ssh", "-n", "training")
    assert result.exit_code == 0, result.output
    assert "allowed by this cluster's login-node policy" in result.output


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"spec__loginNodesConfig__enableTeleport": None}, "not enabled"),
        ({"spec__loginNodesConfig__enableTeleport": "true"}, "not enabled"),
        ({"status__state": "Updating"}, "requires a Ready Slurm cluster"),
        (
            {"spec__loginNodesConfig__additionalLoginsets": [{"name": "extra"}]},
            "multiple login-node groups",
        ),
        ({"spec__loginNodesConfig__allowGroups": []}, "access policy"),
        ({"status__loginNodeNames": []}, "login-node names"),
        ({"status__teleportCluster": "proxy.example.com:8443"}, "Teleport proxy"),
        ({"metadata__deleted_at": 1}, "being deleted"),
    ],
)
def test_login_ssh_never_starts_tsh_for_unusable_clusters(session, changes, message):
    http, run = session
    with_cluster(http, **changes)
    result = invoke("cluster", "ssh", "-n", "training")
    assert result.exit_code == 1
    assert message in result.output
    run.assert_not_called()


def test_login_ssh_rejects_an_unknown_login_node(session):
    _, run = session
    result = invoke("cluster", "ssh", "-n", "training", "--node", "login-9")
    assert result.exit_code == 1
    assert "login-0, login-1" in result.output
    run.assert_not_called()


def test_login_node_removed_during_sign_in_cannot_connect(session):
    http, run = session
    reads = []

    def clusters(request):
        # Two reads resolve the target; the third revalidates after sign-in.
        reads.append(request)
        cluster = deepcopy(CLUSTER)
        if len(reads) > 2:
            cluster["status"]["loginNodeNames"] = ["login-1"]
        return 200, {}, json.dumps([cluster])

    http.remove(responses.GET, CLUSTERS_URL)
    http.add_callback(responses.GET, CLUSTERS_URL, callback=clusters)
    run.side_effect = [profile(), inventory("login-0"), completed()]
    result = invoke("cluster", "ssh", "-n", "training")
    assert result.exit_code == 1
    assert "changed during sign-in" in result.output
    assert [c.args[0][1] for c in run.call_args_list] == ["status", "ls"]


# --- job allocations -----------------------------------------------------


def test_job_ssh_reads_the_live_scheduler_list_and_connects(session):
    http, run = session
    run.side_effect = [profile(), inventory("gpu-1"), completed()]
    result = invoke("job", "ssh", "--id", "42", "--cluster", "training")
    assert result.exit_code == 0, result.output
    assert "Connecting to node gpu-1 of Slurm job 42 as alice_corp" in result.output
    job_calls = [c for c in http.calls if c.request.url.startswith(JOBS_URL)]
    query = job_calls[0].request.params
    assert {k: query[k] for k in ("job_query_mode", "status", "q")} == {
        "job_query_mode": "alive_only",
        "status": "running",
        "q": "42",
    }
    assert ssh_args(run)[-1] == "alice_corp@host-uuid-1"


def test_job_ssh_resolves_the_owning_cluster(session):
    http, run = session
    http.get(
        f"{BASE}/slurm/jobs",
        json={
            "jobs": [{**JOB, "slurm_cluster": {"id": "slurm/training"}}],
            "total": 1,
        },
    )
    run.side_effect = [profile(), inventory("gpu-1"), completed()]
    result = invoke("job", "ssh", "--id", "42")
    assert result.exit_code == 0, result.output


def test_job_ssh_requires_a_node_for_multi_node_jobs(session):
    http, run = session
    job = deepcopy(JOB)
    job["status"]["nodes"] = ["gpu-2", "gpu-1"]
    http.replace(responses.GET, JOBS_URL, json={"jobs": [job], "total": 1})
    result = invoke("job", "ssh", "--id", "42", "-c", "training")
    assert result.exit_code == 1
    assert "runs on 2 nodes. Select one with --node: gpu-1, gpu-2" in result.output
    run.assert_not_called()

    run.side_effect = [profile(), inventory("gpu-2"), completed()]
    result = invoke("job", "ssh", "--id", "42", "-c", "training", "--node", "gpu-2")
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize(
    "jobs, message",
    [
        ([], "no current running allocation"),
        ([{**JOB, "metadata": {**JOB["metadata"], "owner": "bob"}}], "(alice_corp)"),
        (
            [{**JOB, "status": {**JOB["status"], "job_state": "COMPLETING"}}],
            "current running Slurm allocation",
        ),
        ([{**JOB, "status": {**JOB["status"], "nodes": []}}], "allocated node"),
        ([JOB, JOB], "ambiguous"),
    ],
)
def test_job_ssh_never_guesses_an_allocation(session, jobs, message):
    http, run = session
    http.replace(responses.GET, JOBS_URL, json={"jobs": jobs, "total": len(jobs)})
    result = invoke("job", "ssh", "--id", "42", "-c", "training")
    assert result.exit_code == 1
    assert message in result.output
    run.assert_not_called()


def test_job_ssh_requires_teleport_on_a_compute_group(session):
    http, run = session
    with_cluster(http, spec__gpuNodeGroupsConfig={"groups": [{"id": "gpu-group"}]})
    result = invoke("job", "ssh", "--id", "42", "-c", "training")
    assert result.exit_code == 1
    assert "compute node groups" in result.output
    run.assert_not_called()


# --- Slurm Dev Pods ------------------------------------------------------


def test_devpod_teleport_uses_the_reported_node_and_account(session):
    _, run = session
    run.side_effect = [profile(["alice"]), inventory("training-alice"), completed()]
    result = invoke("devpod", "ssh", "-n", "training-alice", "--transport", "teleport")
    assert result.exit_code == 0, result.output
    assert "Connecting to Slurm Dev Pod slurm-training/training-alice" in result.output
    assert ssh_args(run) == [
        "/usr/bin/tsh",
        "ssh",
        "--proxy=proxy.example.com:443",
        "--cluster=teleport-root.example.com",
        "--user=alice@example.com",
        "alice@host-uuid-1",
    ]
    login = [c for c in run.call_args_list if c.args[0][1] == "login"]
    assert login == []


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"metadata": {"owner": "bob@example.com"}}, "you own"),
        ({"status": {"state": "NotReady"}}, "is not Ready"),
        ({"status": {"teleportNodeName": None}}, "does not report a Teleport node"),
        ({"status": {"teleportNodeName": "other-pod"}}, "complete Teleport target"),
        ({"status": {"teleportCluster": "https://proxy"}}, "Teleport proxy"),
    ],
)
def test_devpod_teleport_never_connects_to_an_unverified_pod(session, changes, message):
    http, run = session
    pod = deepcopy(DEVPOD)
    for section, values in changes.items():
        pod[section].update(values)
    http.replace(responses.GET, DEVPOD_URL, json=pod)
    result = invoke("devpod", "ssh", "-n", "training-alice", "--transport", "teleport")
    assert result.exit_code == 1
    assert message in result.output
    run.assert_not_called()


@pytest.mark.parametrize(
    "args",
    [
        ["--transport", "teleport", "--print-only"],
        ["--transport", "teleport", "--", "-v"],
        ["--teleport-auth", "SSO"],
    ],
)
def test_devpod_transport_options_do_not_mix(args):
    with patch("leptonai.cli.slurm.APIClient") as client:
        result = invoke("devpod", "ssh", "-n", "training-alice", *args)
    assert result.exit_code == 2, result.output
    client.assert_not_called()
