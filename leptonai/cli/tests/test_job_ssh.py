"""Job replica selection and Teleport discovery through the actual CLI/API seam."""

from datetime import datetime, timedelta, timezone
import json
import os
import subprocess
import tempfile
from unittest.mock import patch

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

import pytest
import responses
from click.testing import CliRunner

from leptonai.api.v2.client import APIClient
from leptonai.cli.job import job


BASE = "https://gw.example/api/v2/workspaces/ws-job-ssh"
JOB_URL = f"{BASE}/jobs/train-id"
REPLICAS_URL = f"{JOB_URL}/replicas"
HOST = "ws-job-ssh-worker-1"
PROXY = "proxy.example.com"


def job_body(state="Running", name="train", id="train-id"):
    return {"metadata": {"id": id, "name": name}, "status": {"state": state}}


def replica(id="worker-1", reason="Ready"):
    return {"metadata": {"id": id}, "status": {"readiness_issue": {"reason": reason}}}


def result(code=0, stdout="", stderr=""):
    return subprocess.CompletedProcess([], code, stdout, stderr)


def profile(proxy=PROXY, cluster=PROXY, expired=False):
    return result(
        stdout=json.dumps({
            "active": {
                "profile_url": f"https://{proxy}",
                "cluster": cluster,
                "username": "alice@example.com",
                "logins": ["root"],
                "valid_until": (
                    datetime.now(timezone.utc) + timedelta(hours=-1 if expired else 1)
                ).isoformat(),
            }
        })
    )


def node(hostname=HOST, workspace="ws-job-ssh", id="node-uuid"):
    return {
        "kind": "node",
        "metadata": {"name": id, "labels": {"teleport.lepton.ai/workspace": workspace}},
        "spec": {"hostname": hostname},
    }


@pytest.fixture
def session():
    client = APIClient(workspace_id="ws-job-ssh", auth_token="test-token", url=BASE)
    with (
        responses.RequestsMock() as http,
        patch("leptonai.cli.job.APIClient", return_value=client),
        patch("leptonai.cli.teleport.shutil.which", return_value="/usr/bin/tsh"),
        # Client preflight is exercised separately in test_teleport_preflight.py.
        patch("leptonai.cli.teleport._check_tsh_version"),
        patch("leptonai.cli.teleport.subprocess.run") as run,
    ):
        yield http, run


def register(http, *, state="Running", replicas=None):
    http.get(JOB_URL, json=job_body(state))
    if state == "Running":
        http.get(REPLICAS_URL, json=[replica()] if replicas is None else replicas)


def invoke(*extra):
    return CliRunner().invoke(job, ["ssh", "--id", "train-id", *extra])


def test_single_replica_uses_active_proxy_and_exact_node_id(session):
    http, run = session
    register(http)
    run.side_effect = [
        profile(),
        profile(),
        result(stdout=json.dumps([node()])),
        result(),
    ]
    output = invoke()
    assert output.exit_code == 0, output.output
    assert [c.args[0][1] for c in run.call_args_list] == [
        "status",
        "status",
        "ls",
        "ssh",
    ]
    listing = run.call_args_list[2]
    assert listing.args[0] == [
        "/usr/bin/tsh",
        "ls",
        "--proxy=proxy.example.com:443",
        "--cluster=proxy.example.com",
        "--user=alice@example.com",
        "--format=json",
        f"--search={HOST}",
        "teleport.lepton.ai/workspace=ws-job-ssh",
    ]
    assert listing.kwargs["timeout"] == 15
    assert run.call_args.args[0][-1] == "root@node-uuid"
    assert run.call_args.kwargs == {"check": False}
    assert "worker-1" in output.output
    assert len(http.calls) == 4  # Job and replica checks both before and after login.
    assert all("job_query_mode=alive_only" in c.request.url for c in http.calls)


def test_explicit_proxy_logs_in_without_an_active_profile(session):
    http, run = session
    register(http)
    run.side_effect = [
        result(1, stderr="ERROR: Not logged in."),
        result(),
        profile(),
        result(stdout=json.dumps([node()])),
        result(),
    ]
    output = invoke("--teleport-proxy", PROXY, "--teleport-auth", "Custom SSO")
    assert output.exit_code == 0, output.output
    assert run.call_args_list[1].args[0] == [
        "/usr/bin/tsh",
        "login",
        "--proxy=proxy.example.com:443",
        "--auth=Custom SSO",
        "proxy.example.com",
    ]
    assert run.call_args_list[1].kwargs == {"check": False}


def test_active_profile_with_distinct_cluster_is_preserved(session):
    http, run = session
    register(http)
    run.side_effect = [
        profile(cluster="cluster.example.com"),
        profile(cluster="cluster.example.com"),
        result(stdout=json.dumps([node()])),
        result(),
    ]
    output = invoke()
    assert output.exit_code == 0, output.output
    assert "--cluster=cluster.example.com" in run.call_args.args[0]


@pytest.mark.parametrize("code", [7, 130, 255, -15])
def test_ssh_exit_status_is_preserved(session, code):
    http, run = session
    register(http)
    run.side_effect = [
        profile(),
        profile(),
        result(stdout=json.dumps([node()])),
        result(code=code),
    ]
    output = invoke()
    assert output.exit_code == (code if code > 0 else 128 - code)


def test_expired_active_profile_can_discover_proxy_then_login(session):
    http, run = session
    register(http)
    run.side_effect = [
        profile(expired=True),
        profile(expired=True),
        result(),
        profile(),
        result(stdout=json.dumps([node()])),
        result(),
    ]
    output = invoke()
    assert output.exit_code == 0, output.output
    assert run.call_args_list[2].args[0][1] == "login"


def test_no_profile_requires_proxy_without_attempting_login(session):
    http, run = session
    register(http)
    run.return_value = result(1, stderr="ERROR: Not logged in.")
    output = invoke()
    assert output.exit_code == 1
    assert "--teleport-proxy" in output.output
    assert run.call_count == 1


@pytest.mark.parametrize(
    "bad_proxy",
    [
        "https://proxy.example.com",
        "user@proxy.example.com",
        "proxy.example.com/path",
        "proxy.example.com:0",
        "proxy.example.com:65536",
        "proxy.example.com\n",
    ],
)
def test_invalid_proxy_never_invokes_tsh(session, bad_proxy):
    http, run = session
    register(http)
    output = invoke("--teleport-proxy", bad_proxy)
    assert output.exit_code == 1
    run.assert_not_called()


def test_multiple_ready_replicas_require_selection(session):
    http, run = session
    register(http, replicas=[replica(), replica("worker-2")])
    output = invoke()
    assert output.exit_code == 1
    assert "--replica" in output.output
    run.assert_not_called()


def test_selected_replica_is_used(session):
    http, run = session
    register(http, replicas=[replica(), replica("worker-2")])
    run.side_effect = [
        profile(),
        profile(),
        result(stdout=json.dumps([node(hostname="ws-job-ssh-worker-2")])),
        result(),
    ]
    output = invoke("--replica", "worker-2")
    assert output.exit_code == 0, output.output
    assert "--search=ws-job-ssh-worker-2" in run.call_args_list[2].args[0]


@pytest.mark.parametrize(
    "selection, reason",
    [("foreign", "Ready"), ("worker-1", "Deleted"), ("worker-1", "InProgress")],
)
def test_unowned_or_not_ready_replica_is_rejected(session, selection, reason):
    http, run = session
    register(http, replicas=[replica(reason=reason)])
    output = invoke("--replica", selection)
    assert output.exit_code == 1
    run.assert_not_called()


def test_historical_replicas_are_excluded_from_automatic_selection(session):
    http, run = session
    register(http, replicas=[replica("old-worker", "Deleted"), replica()])
    run.side_effect = [
        profile(),
        profile(),
        result(stdout=json.dumps([node()])),
        result(),
    ]
    output = invoke()
    assert output.exit_code == 0, output.output
    assert f"--search={HOST}" in run.call_args_list[2].args[0]


@pytest.mark.parametrize(
    "replicas",
    [[], [replica(reason="InProgress")], [replica(), {}], [replica(), replica()], {}],
)
def test_missing_or_malformed_replica_list_never_invokes_tsh(session, replicas):
    http, run = session
    register(http, replicas=replicas)
    output = invoke()
    assert output.exit_code == 1
    run.assert_not_called()


@pytest.mark.parametrize(
    "state", ["Completed", "Failed", "Archived", "Starting", "Stopped"]
)
def test_only_running_jobs_can_connect(session, state):
    http, run = session
    register(http, state=state)
    output = invoke()
    assert output.exit_code == 1
    assert "running job" in output.output
    run.assert_not_called()


@pytest.mark.parametrize(
    "nodes, message",
    [
        ([], "No Teleport node"),
        ([node(hostname=HOST + "-old")], "No Teleport node"),
        ([node(workspace="other-workspace")], "No Teleport node"),
        ([node(), node(id="another-id")], "Multiple Teleport nodes"),
        ([node(id="--option")], "invalid node list"),
        ({}, "invalid node list"),
        ([{}], "invalid node list"),
    ],
)
def test_node_discovery_never_guesses_or_connects_to_unverified_targets(
    session, nodes, message
):
    http, run = session
    register(http)
    run.side_effect = [profile(), profile(), result(stdout=json.dumps(nodes))]
    output = invoke()
    assert output.exit_code == 1
    assert message in output.output
    assert run.call_count == 3


@pytest.mark.parametrize(
    "failure, message",
    [
        (result(1, stderr="access denied"), "Could not list Teleport nodes"),
        (subprocess.TimeoutExpired("tsh ls", 15), "Timed out discovering"),
        (result(stdout="invalid JSON"), "invalid node list"),
    ],
)
def test_node_lookup_failures_are_actionable(session, failure, message):
    http, run = session
    register(http)
    run.side_effect = [profile(), profile(), failure]
    output = invoke()
    assert output.exit_code == 1
    assert message in output.output
    assert run.call_count == 3


def test_replica_disappearing_during_login_cannot_connect(session):
    http, run = session
    http.get(JOB_URL, json=job_body())
    http.get(REPLICAS_URL, json=[replica()])
    http.get(REPLICAS_URL, json=[replica("replacement")])
    run.side_effect = [profile(), profile()]
    output = invoke()
    assert output.exit_code == 1
    assert "does not belong to the current job run" in output.output
    assert run.call_count == 2


@pytest.mark.parametrize(
    "names, message", [([], "No live job"), (["train", "train"], "Multiple jobs")]
)
def test_name_must_resolve_to_one_exact_job(session, names, message):
    http, run = session
    http.get(f"{BASE}/jobs", json={"jobs": [job_body(name=n) for n in names]})
    if names:
        http.get(f"{BASE}/jobs", json={"jobs": []})
    output = CliRunner().invoke(job, ["ssh", "--name", "train"])
    assert output.exit_code == 1
    assert message in output.output
    run.assert_not_called()


def test_exact_name_resolves_to_job_id(session):
    http, run = session
    http.get(
        f"{BASE}/jobs",
        json={"jobs": [job_body(), job_body(name="train-other", id="other")]},
    )
    http.get(f"{BASE}/jobs", json={"jobs": []})
    register(http)
    run.side_effect = [
        profile(),
        profile(),
        result(stdout=json.dumps([node()])),
        result(),
    ]
    output = CliRunner().invoke(job, ["ssh", "--name", "train"])
    assert output.exit_code == 0, output.output


@pytest.mark.parametrize("args", [[], ["--id", "id", "--name", "name"]])
def test_exactly_one_job_selector_is_required(args):
    with patch("leptonai.cli.job.APIClient") as client:
        output = CliRunner().invoke(job, ["ssh", *args])
    assert output.exit_code == 2
    client.assert_not_called()
