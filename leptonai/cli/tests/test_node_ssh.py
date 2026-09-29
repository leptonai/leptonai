"""Node SSH discovery, identity and terminal handoff without live credentials."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import subprocess
from unittest.mock import patch

import pytest
import responses
from click.testing import CliRunner

from leptonai.api.v2.client import APIClient
from leptonai.cli.node import node


BASE = "https://gw.example/api/v2/workspaces/ws-node"
TOKEN = "nvapi-" + "a" * 40
GROUP = {
    "metadata": {"id": "gpu-group", "name": "training-gpus"},
    "spec": {},
    "status": {},
}
CLUSTER = {
    "metadata": {"id": "slurm/training", "name": "training", "uuid": "cluster-1"},
    "spec": {
        "gpuNodeGroupsConfig": {
            "groups": [{"id": "gpu-group", "enableTeleport": True}]
        },
        "ldapConfig": {"domainSuffix": {"example.com": "_corp"}},
    },
    "status": {"teleportCluster": "proxy.example.com"},
}
NODE = {
    "metadata": {"id": "node-1", "created_at": 1000},
    "spec": {"dedicated_node_group": "gpu-group", "machine_id": "machine-1"},
}
MACHINE = {
    "metadata": {"name": "machine-cr-1"},
    "status": {
        "machine_id": "machine-1",
        "node_name": "node-1",
        "hostname": "physical-1",
    },
}
INVENTORY = [{
    "kind": "node",
    "metadata": {
        "name": "host-uuid-1",
        "labels": {
            "teleport.lepton.ai/slurm-cluster": "training",
            "cluster": "training",
            "hostname": "physical-1",
        },
    },
    # The runtime hostname label is deliberately different from spec.hostname.
    "spec": {"hostname": "slurm-compute-container"},
}]
NODE_URL = f"{BASE}/dedicated-node-groups/gpu-group/nodes/node-1"
MACHINE_URL = f"{BASE}/dedicated-node-groups/gpu-group/machines/machine-1"


def completed(stdout="", code=0, stderr=""):
    return subprocess.CompletedProcess([], code, stdout, stderr)


def profile(**overrides):
    active = {
        "profile_url": "https://proxy.example.com:443",
        "cluster": "teleport-root.example.com",
        "username": "alice@example.com",
        "valid_until": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "logins": ["alice_corp"],
    }
    active.update(overrides)
    return completed(json.dumps({"active": active}))


@pytest.fixture
def session():
    client = APIClient(workspace_id="ws-node", auth_token=TOKEN, url=BASE)
    with (
        responses.RequestsMock(assert_all_requests_are_fired=False) as http,
        patch("leptonai.cli.node.get_client", return_value=client),
        patch("leptonai.cli.util.get_client", return_value=client),
        patch("leptonai.cli.teleport._require_tsh", return_value="/usr/bin/tsh"),
        patch("leptonai.cli.teleport.subprocess.run") as run,
    ):
        http.get(f"{BASE}/dedicated-node-groups", json=[GROUP])
        http.get(BASE, json={"name": "ws-node", "role": "user"})
        http.get(
            f"{BASE}/tokens",
            json=[{
                "masked_value": "nvapi-aaaaaa...aaaaaa",
                "created_by": "alice@example.com",
            }],
        )
        http.get(f"{BASE}/slurmclusters", json=[CLUSTER])
        http.get(NODE_URL, json=NODE)
        http.get(MACHINE_URL, json=MACHINE)
        run.side_effect = [profile(), completed(json.dumps(INVENTORY)), completed()]
        yield http, run, client


def invoke(*extra, group="gpu-group"):
    return CliRunner().invoke(node, ["ssh", "-ng", group, "--id", "node-1", *extra])


def test_resolves_machine_hostname_and_connects_by_host_id(session):
    http, run, _ = session
    result = invoke(group="training-gpus")
    assert result.exit_code == 0, result.output
    assert run.call_args.args[0] == [
        "/usr/bin/tsh",
        "ssh",
        "--proxy=proxy.example.com:443",
        "--cluster=teleport-root.example.com",
        "--user=alice@example.com",
        "alice_corp@host-uuid-1",
    ]
    assert run.call_args.kwargs == {"check": False}
    discovery = run.call_args_list[1]
    assert (
        discovery.args[0][-1]
        == "teleport.lepton.ai/slurm-cluster=training,cluster=training"
    )
    assert discovery.kwargs["stdin"] == subprocess.DEVNULL
    assert sum(call.request.url == MACHINE_URL for call in http.calls) == 2


@pytest.mark.parametrize(
    "initial",
    [
        completed(code=1, stderr="not logged in"),
        profile(username="bob@example.com"),
        profile(profile_url="https://other.example.com"),
        profile(valid_until="2000-01-01T00:00:00Z"),
    ],
)
def test_login_uses_expected_personal_identity_and_discovers_cluster(session, initial):
    _, run, _ = session
    run.side_effect = [
        initial,
        completed(),
        profile(),
        completed(json.dumps(INVENTORY)),
        completed(),
    ]
    result = invoke("--teleport-auth", "Custom SSO")
    assert result.exit_code == 0, result.output
    assert run.call_args_list[1].args[0] == [
        "/usr/bin/tsh",
        "login",
        "--proxy=proxy.example.com:443",
        "--auth=Custom SSO",
        "--user=alice@example.com",
    ]


def test_login_with_wrong_user_cannot_connect(session):
    _, run, _ = session
    run.side_effect = [
        profile(username="bob@example.com"),
        completed(),
        profile(username="bob@example.com"),
    ]
    result = invoke()
    assert result.exit_code == 1
    assert "did not produce a valid profile" in result.output
    assert run.call_count == 3


def test_missing_slurm_principal_cannot_connect(session):
    _, run, _ = session
    run.side_effect = [profile(logins=["root"])]
    result = invoke()
    assert result.exit_code == 1
    assert "not authorized to log in as alice_corp" in result.output
    assert run.call_count == 1


@pytest.mark.parametrize("role", ["viewer", "service", None])
def test_requires_workspace_user_or_admin(session, role):
    http, run, _ = session
    http.replace(responses.GET, BASE, json={"name": "ws-node", "role": role})
    result = invoke()
    assert result.exit_code == 1
    assert "user or admin" in result.output
    run.assert_not_called()


@pytest.mark.parametrize(
    "tokens",
    [
        [],
        {},
        [{"masked_value": "nvapi-xxxxxx...xxxxxx", "created_by": "alice@example.com"}],
        [{"masked_value": "nvapi-aaaaaa...aaaaaa", "created_by": "Alice@example.com"}],
        [{"masked_value": "nvapi-aaaaaa...aaaaaa", "created_by": "alice@example.com"}]
        * 2,
    ],
)
def test_requires_unambiguous_personal_token_owner(session, tokens):
    http, run, _ = session
    http.replace(responses.GET, f"{BASE}/tokens", json=tokens)
    result = invoke()
    assert result.exit_code == 1
    assert TOKEN not in result.output
    run.assert_not_called()


@pytest.mark.parametrize(
    "clusters, message",
    [([], "no Slurm"), ([CLUSTER, CLUSTER], "multiple Slurm"), ({}, "Invalid Slurm")],
)
def test_cluster_ownership_must_be_unique(session, clusters, message):
    http, run, _ = session
    http.replace(responses.GET, f"{BASE}/slurmclusters", json=clusters)
    result = invoke()
    assert result.exit_code == 1
    assert message in result.output
    run.assert_not_called()


@pytest.mark.parametrize(
    "path, value, message",
    [
        (
            ("spec", "gpuNodeGroupsConfig", "groups", 0, "enableTeleport"),
            False,
            "Enable Teleport",
        ),
        (
            ("spec", "gpuNodeGroupsConfig", "groups", 0, "enableTeleport"),
            "true",
            "Enable Teleport",
        ),
        (("spec", "usePodNetworking"), True, "Pod Networking"),
        (("spec", "usePodNetworking"), "false", "networking configuration"),
        (("metadata", "id"), "wrong/training-other", "cluster identity"),
        (("metadata", "deleted_at"), 1, "being deleted"),
        (
            ("status", "teleportCluster"),
            "https://proxy.example.com",
            "valid Teleport proxy",
        ),
        (
            ("status", "teleportCluster"),
            "proxy.example.com:8443",
            "valid Teleport proxy",
        ),
        (("status", "teleportCluster"), "proxy.example.com\n", "valid Teleport proxy"),
        (
            ("spec", "ldapConfig", "domainSuffix", "example.com"),
            ";root",
            "Linux username",
        ),
    ],
)
def test_invalid_or_disabled_cluster_never_launches_tsh(session, path, value, message):
    http, run, _ = session
    cluster = deepcopy(CLUSTER)
    parent = cluster
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value
    http.replace(responses.GET, f"{BASE}/slurmclusters", json=[cluster])
    result = invoke()
    assert result.exit_code == 1
    assert message in result.output
    run.assert_not_called()


@pytest.mark.parametrize(
    "resource, section, key, value",
    [
        ("node", "metadata", "id", "other-node"),
        ("node", "spec", "dedicated_node_group", "other-group"),
        ("node", "spec", "machine_id", None),
        ("machine", "status", "machine_id", "other-machine"),
        ("machine", "status", "node_name", "other-node"),
        ("machine", "status", "hostname", None),
        ("machine", "metadata", "deleted_at", 1),
    ],
)
def test_node_and_machine_must_match(session, resource, section, key, value):
    http, run, _ = session
    record = deepcopy(NODE if resource == "node" else MACHINE)
    record[section][key] = value
    http.replace(
        responses.GET, NODE_URL if resource == "node" else MACHINE_URL, json=record
    )
    result = invoke()
    assert result.exit_code == 1
    run.assert_not_called()


@pytest.mark.parametrize("kind", ["machine", "cluster", "owner"])
def test_revalidates_after_sso_and_rejects_changed_target(session, kind):
    http, run, _ = session
    if kind == "machine":
        record = deepcopy(MACHINE)
        record["status"]["hostname"] = "replacement-host"
        http.get(MACHINE_URL, json=record)
    elif kind == "cluster":
        record = deepcopy(CLUSTER)
        record["metadata"]["uuid"] = "replacement-cluster"
        http.get(f"{BASE}/slurmclusters", json=[record])
    else:
        http.get(
            f"{BASE}/tokens",
            json=[{
                "masked_value": "nvapi-aaaaaa...aaaaaa",
                "created_by": "bob@example.com",
            }],
        )
    run.side_effect = [
        completed(code=1, stderr="not logged in"),
        completed(),
        profile(),
        completed(json.dumps(INVENTORY)),
    ]
    result = invoke()
    assert result.exit_code == 1
    assert "changed during sign-in" in result.output
    assert all(call.args[0][1] != "ssh" for call in run.call_args_list)


@pytest.mark.parametrize(
    "inventory, message",
    [
        ([], "No Teleport node"),
        (INVENTORY * 2, "Multiple Teleport nodes"),
        ({}, "invalid node list"),
    ],
)
def test_inventory_requires_one_match(session, inventory, message):
    _, run, _ = session
    run.side_effect = [profile(), completed(json.dumps(inventory))]
    result = invoke()
    assert result.exit_code == 1
    assert message in result.output
    assert run.call_count == 2


@pytest.mark.parametrize(
    "label", ["teleport.lepton.ai/slurm-cluster", "cluster", "hostname"]
)
def test_rechecks_labels_even_if_tsh_returns_out_of_scope_nodes(session, label):
    _, run, _ = session
    inventory = deepcopy(INVENTORY)
    inventory[0]["metadata"]["labels"][label] = "other"
    run.side_effect = [profile(), completed(json.dumps(inventory))]
    result = invoke()
    assert result.exit_code == 1
    assert "No Teleport node" in result.output


@pytest.mark.parametrize(
    "failure, message",
    [
        (completed(code=1), "Could not list"),
        (completed("invalid json"), "invalid node list"),
        (subprocess.TimeoutExpired("tsh", 15), "Timed out"),
    ],
)
def test_discovery_errors_never_start_ssh(session, failure, message):
    _, run, _ = session
    run.side_effect = [profile(), failure]
    result = invoke()
    assert result.exit_code == 1
    assert message in result.output
    assert run.call_count == 2


@pytest.mark.parametrize("status", [403, 404, 500])
@pytest.mark.parametrize(
    "path",
    [
        "/tokens",
        "/slurmclusters",
        "/dedicated-node-groups/gpu-group/machines/machine-1",
    ],
)
def test_api_errors_do_not_expose_response_body_or_spawn_tsh(session, status, path):
    http, run, _ = session
    http.replace(responses.GET, BASE + path, status=status, body=TOKEN)
    result = invoke()
    assert result.exit_code == 1
    assert f"HTTP {status}" in result.output
    assert TOKEN not in result.output
    run.assert_not_called()


@pytest.mark.parametrize("code", [0, 42, 255, -15])
def test_preserves_ssh_exit_status(session, code):
    _, run, _ = session
    run.side_effect = [
        profile(),
        completed(json.dumps(INVENTORY)),
        completed(code=code),
    ]
    result = invoke()
    assert result.exit_code == (code if code >= 0 else 128 - code)


def test_group_selection_requires_exact_match(session):
    _, run, _ = session
    result = invoke(group="gpu")
    assert result.exit_code == 1
    assert "exactly one node group" in result.output
    run.assert_not_called()
