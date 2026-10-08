"""Pod discovery and tsh session regressions, without network or SSH access."""

from datetime import datetime, timedelta, timezone
import json
import os
import subprocess
import tempfile
from unittest.mock import patch
from types import SimpleNamespace

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

import pytest
import requests
import responses
from click.testing import CliRunner

from leptonai.api.v2.client import APIClient, reset_new_deployment_api_flag_cache
from leptonai.cli.pod import pod


BASE = "https://gw.example/api/v2/workspaces/ws-teleport"
REPLICAS = f"{BASE}/deployments/my-pod/replicas"
CONNECTION_URL = f"{REPLICAS}/replica-1/teleport-connectivity"
CONNECTION = {
    "name": "ws-teleport-my-pod",
    "status": "Running",
    "proxy": "proxy.example.com",
    "port": 443,
    "clusterDomain": "cluster.example.com",
    "username": "root",
}


def profile(**overrides):
    active = {
        "profile_url": "https://proxy.example.com:443",
        "cluster": "cluster.example.com",
        "username": "alice@example.com",
        "valid_until": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "logins": ["root"],
    }
    active.update(overrides)
    return subprocess.CompletedProcess([], 0, json.dumps({"active": active}), "")


def completed(code=0):
    return subprocess.CompletedProcess([], code, "", "")


def logged_out():
    return subprocess.CompletedProcess([], 1, "", "ERROR: Not logged in.\n")


@pytest.fixture
def session():
    reset_new_deployment_api_flag_cache()
    client = APIClient(workspace_id="ws-teleport", auth_token="test-token", url=BASE)
    with (
        responses.RequestsMock() as http,
        patch.object(
            APIClient, "_resolve_new_deployment_api", return_value=False
        ) as flag,
        patch("leptonai.cli.pod.APIClient", return_value=client),
        patch(
            "leptonai.cli.teleport.shutil.which", return_value="/usr/bin/tsh"
        ) as which,
        # Client preflight is exercised separately in test_teleport_preflight.py.
        patch("leptonai.cli.teleport._check_tsh_version"),
        patch("leptonai.cli.teleport.subprocess.run") as run,
    ):
        yield http, flag, which, run
    reset_new_deployment_api_flag_cache()


def register(http, *, connection=None, replicas=None):
    http.get(
        REPLICAS,
        json=replicas if replicas is not None else [{"metadata": {"id": "replica-1"}}],
    )
    if replicas is None:
        http.get(CONNECTION_URL, json=CONNECTION if connection is None else connection)


def invoke(*extra):
    return CliRunner().invoke(
        pod, ["ssh", "-n", "my-pod", "--transport", "teleport", *extra]
    )


def test_reuses_profile_without_public_ip_or_port_mapping(session):
    http, _, _, run = session
    register(http)
    run.side_effect = [profile(), completed()]
    result = invoke()
    assert result.exit_code == 0, result.output
    assert [c.request.url for c in http.calls] == [REPLICAS, CONNECTION_URL]
    assert run.call_args_list[0].args[0] == [
        "/usr/bin/tsh",
        "status",
        "--proxy=proxy.example.com:443",
        "--format=json",
    ]
    assert run.call_args_list[0].kwargs["timeout"] == 10
    assert run.call_args.args[0] == [
        "/usr/bin/tsh",
        "ssh",
        "--proxy=proxy.example.com:443",
        "--cluster=cluster.example.com",
        "--user=alice@example.com",
        "root@ws-teleport-my-pod",
    ]
    assert run.call_args.kwargs == {"check": False}


def test_tsh_v18_status_does_not_require_unsupported_client_flag(session):
    http, _, _, run = session
    register(http)

    def tsh_v18(args, **kwargs):
        if args[1] == "status":
            if "--client" in args:
                return subprocess.CompletedProcess(
                    args, 1, "", "tsh: error: unknown long flag '--client'"
                )
            return profile()
        return completed()

    run.side_effect = tsh_v18
    result = invoke()
    assert result.exit_code == 0, result.output
    assert [call.args[0][1] for call in run.call_args_list] == ["status", "ssh"]


def test_status_command_error_does_not_start_sso_login(session):
    http, _, _, run = session
    register(http)
    run.return_value = subprocess.CompletedProcess(
        [], 1, "", "tsh: error: unknown long flag '--example'"
    )
    result = invoke()
    assert result.exit_code == 1
    assert "Could not check the local Teleport login" in result.output
    assert "Signing in" not in result.output
    assert run.call_count == 1


def test_expired_json_profile_with_nonzero_status_can_log_in(session):
    http, _, _, run = session
    register(http)
    expired = profile(valid_until="2020-01-01T00:00:00Z")
    expired.returncode = 1
    run.side_effect = [expired, completed(), profile(), completed()]
    result = invoke()
    assert result.exit_code == 0, result.output
    assert run.call_args_list[1].args[0][1] == "login"


@pytest.mark.parametrize(
    "initial",
    [
        logged_out(),
        profile(valid_until="2020-01-01T00:00:00Z"),
        profile(profile_url="https://another.example.com:443"),
        profile(cluster="another-cluster"),
    ],
)
def test_missing_expired_or_wrong_profile_logs_in_and_rechecks(session, initial):
    http, _, _, run = session
    register(http)
    run.side_effect = [initial, completed(), profile(), completed()]
    result = invoke()
    assert result.exit_code == 0, result.output
    assert "Signing in" in result.output
    assert run.call_args_list[1].args[0] == [
        "/usr/bin/tsh",
        "login",
        "--proxy=proxy.example.com:443",
        "--auth=Starfleet",
        "cluster.example.com",
    ]
    assert run.call_args_list[1].kwargs == {"check": False}
    assert run.call_args_list[2].args[0][1] == "status"


def test_auth_override_is_passed_as_one_argument(session):
    http, _, _, run = session
    register(http)
    run.side_effect = [logged_out(), completed(), profile(), completed()]
    result = invoke("--teleport-auth", "Custom SSO")
    assert result.exit_code == 0, result.output
    assert "--auth=Custom SSO" in run.call_args_list[1].args[0]


@pytest.mark.parametrize("code", [1, 42, 130, 255, -15])
def test_ssh_exit_status_is_preserved(session, code):
    http, _, _, run = session
    register(http)
    run.side_effect = [profile(), completed(code)]
    result = invoke()
    assert result.exit_code == (code if code > 0 else 128 - code)


def test_failed_login_never_starts_ssh(session):
    http, _, _, run = session
    register(http)
    run.side_effect = [logged_out(), completed(7)]
    result = invoke()
    assert result.exit_code == 7
    assert run.call_count == 2


def test_successful_login_without_correct_profile_never_starts_ssh(session):
    http, _, _, run = session
    register(http)
    run.side_effect = [logged_out(), completed(), profile(cluster="wrong")]
    result = invoke()
    assert result.exit_code == 1
    assert "did not produce a valid profile" in result.output
    assert run.call_count == 3


def test_missing_login_principal_does_not_retry_login_or_connect(session):
    http, _, _, run = session
    register(http)
    run.return_value = profile(logins=["ubuntu"])
    result = invoke()
    assert result.exit_code == 1
    assert "not authorized to log in as root" in result.output
    assert run.call_count == 1


@pytest.mark.parametrize(
    "bad_profile",
    [
        subprocess.CompletedProcess([], 0, "invalid json", ""),
        profile(valid_until="bad date"),
        profile(valid_until="2030-01-01T00:00:00"),
        profile(logins="root"),
        profile(username=None),
        profile(username="alice\0@example.com"),
    ],
)
def test_invalid_profile_fails_without_starting_login_or_ssh(session, bad_profile):
    http, _, _, run = session
    register(http)
    run.return_value = bad_profile
    result = invoke()
    assert result.exit_code == 1
    assert "Could not read the local Teleport profile" in result.output
    assert run.call_count == 1


@pytest.mark.parametrize(
    "error, message",
    [
        (subprocess.TimeoutExpired("tsh", 10), "Timed out"),
        (FileNotFoundError("tsh disappeared"), "Could not run Teleport"),
    ],
)
def test_tool_errors_are_actionable(session, error, message):
    http, _, _, run = session
    register(http)
    run.side_effect = error
    result = invoke()
    assert result.exit_code == 1
    assert message in result.output


def test_missing_tsh_has_installation_hint(session):
    http, _, which, run = session
    register(http)
    which.return_value = None
    result = invoke()
    assert result.exit_code == 1
    assert "not found in PATH" in result.output
    run.assert_not_called()


@pytest.mark.parametrize(
    "connection, message",
    [
        ({"code": "OK", "message": "teleport not enabled"}, "not enabled"),
        ({**CONNECTION, "status": "NotRunning"}, "not reporting a running"),
        ({"status": "Running", "name": "my-pod"}, "incomplete or invalid"),
        ({**CONNECTION, "port": True}, "incomplete or invalid"),
        ({**CONNECTION, "port": 65536}, "incomplete or invalid"),
        ({**CONNECTION, "proxy": "https://proxy.example.com"}, "incomplete or invalid"),
        ({**CONNECTION, "name": "node; touch /tmp/pwned"}, "incomplete or invalid"),
        ({**CONNECTION, "name": "role=all"}, "incomplete or invalid"),
        ({**CONNECTION, "username": "--option"}, "incomplete or invalid"),
        ({**CONNECTION, "clusterDomain": "--option"}, "incomplete or invalid"),
        ({**CONNECTION, "status": "Unknown"}, "incomplete or invalid"),
    ],
)
def test_unavailable_or_malformed_connection_never_spawns_tsh(
    session, connection, message
):
    http, _, _, run = session
    register(http, connection=connection)
    result = invoke()
    assert result.exit_code == 1
    assert message in result.output
    run.assert_not_called()


@pytest.mark.parametrize("replicas", [[], [{}, {}], {}, [{"metadata": {}}]])
def test_missing_ambiguous_or_invalid_replica_never_queries_connection(
    session, replicas
):
    http, _, _, run = session
    register(http, replicas=replicas)
    result = invoke()
    assert result.exit_code == 1
    assert "replica" in result.output
    assert len(http.calls) == 1
    run.assert_not_called()


@pytest.mark.parametrize("code", [403, 404, 500])
def test_connection_api_error_is_not_treated_as_disabled_or_fallback(session, code):
    http, _, _, run = session
    http.get(REPLICAS, json=[{"metadata": {"id": "replica-1"}}])
    http.get(CONNECTION_URL, status=code, json={"message": "API unavailable"})
    result = invoke()
    assert result.exit_code == 1
    assert str(code) in result.output
    run.assert_not_called()


FEATURES = f"{BASE}/info/features"
DEVPOD = f"{BASE}/devpods/my-pod"
POD_UID = "0f8fad5b-d9cb-469f-a165-70867728950e"


def devpod_body(state="Ready", stopped=None):
    spec = {} if stopped is None else {"stopped": stopped}
    return {"metadata": {"name": "my-pod"}, "spec": spec, "status": {"state": state}}


def devpod_replica(reason="Ready", pod_uid=POD_UID):
    status = {"readiness_issue": {"reason": reason}}
    if pod_uid is not None:
        status["pod_uid"] = pod_uid
    return {"metadata": {"id": "my-pod-0"}, "status": status}


def native_node(hostname="ws-teleport-my-pod", workspace="ws-teleport"):
    return {
        "kind": "node",
        "metadata": {
            "name": "node-uuid",
            "labels": {"teleport.lepton.ai/workspace": workspace},
        },
        "spec": {"hostname": hostname},
    }


def register_native(http, *, features=None, body=None, replicas=None):
    http.get(
        FEATURES, json={"dev_pod_teleport": True} if features is None else features
    )
    if features is not None and features.get("dev_pod_teleport") is not True:
        return
    body = devpod_body() if body is None else body
    http.get(DEVPOD, json=body)
    if body["status"]["state"] != "Ready" or body["spec"].get("stopped"):
        return
    http.get(
        f"{DEVPOD}/replicas", json=[devpod_replica()] if replicas is None else replicas
    )


def test_new_devpod_api_connects_to_the_registered_node(session):
    http, flag, _, run = session
    flag.return_value = True
    register_native(http)
    run.side_effect = [
        profile(profile_url="https://proxy.example.com", cluster="proxy.example.com"),
        profile(profile_url="https://proxy.example.com", cluster="proxy.example.com"),
        subprocess.CompletedProcess([], 0, json.dumps([native_node()]), ""),
        completed(),
    ]
    result = invoke()
    assert result.exit_code == 0, result.output
    assert "Connecting to Dev Pod my-pod via Teleport" in result.output
    # Resolved before sign-in and revalidated before handing over the terminal.
    assert [c.request.url for c in http.calls] == [
        FEATURES,
        DEVPOD,
        f"{DEVPOD}/replicas",
    ] * 2
    listing = run.call_args_list[2].args[0]
    assert "--search=ws-teleport-my-pod" in listing
    assert "teleport.lepton.ai/workspace=ws-teleport" in listing
    assert run.call_args.args[0] == [
        "/usr/bin/tsh",
        "ssh",
        "--proxy=proxy.example.com:443",
        "--cluster=proxy.example.com",
        "--user=alice@example.com",
        "root@node-uuid",
    ]


def test_new_devpod_api_uses_an_explicit_proxy(session):
    http, flag, _, run = session
    flag.return_value = True
    register_native(http)
    run.side_effect = [
        profile(profile_url="https://other.example.com", cluster="other.example.com"),
        subprocess.CompletedProcess([], 0, json.dumps([native_node()]), ""),
        completed(),
    ]
    result = invoke("--teleport-proxy", "other.example.com")
    assert result.exit_code == 0, result.output
    assert run.call_args_list[0].args[0][1:3] == [
        "status",
        "--proxy=other.example.com:443",
    ]
    assert run.call_args.args[0][-1] == "root@node-uuid"


@pytest.mark.parametrize(
    "setup, message",
    [
        ({"features": {}}, "not enabled for Dev Pods"),
        ({"body": devpod_body(state="Starting")}, "is not Ready (state: Starting)"),
        ({"body": devpod_body(stopped=True)}, "state: Stopped"),
        ({"body": devpod_body(state="Deleting")}, "is not Ready (state: Deleting)"),
        ({"replicas": []}, "exactly one Dev Pod replica"),
        ({"replicas": [devpod_replica(reason="Starting")]}, "replica is not Ready"),
        ({"replicas": [devpod_replica(pod_uid=None)]}, "replica identity"),
    ],
)
def test_new_devpod_api_never_connects_to_an_unready_dev_pod(session, setup, message):
    http, flag, _, run = session
    flag.return_value = True
    register_native(http, **setup)
    result = invoke()
    assert result.exit_code == 1
    assert message in result.output
    run.assert_not_called()


def test_new_devpod_api_rejects_a_pod_replaced_during_sign_in(session):
    http, flag, _, run = session
    flag.return_value = True
    register_native(http)
    http.get(f"{DEVPOD}/replicas", json=[devpod_replica(pod_uid=POD_UID[:-1] + "f")])
    run.side_effect = [profile(), profile()]
    result = invoke()
    assert result.exit_code == 1
    assert "restarted or replaced" in result.output
    assert [c.args[0][1] for c in run.call_args_list] == ["status", "status"]


def test_api_failure_while_rechecking_is_not_blamed_on_tsh(session):
    http, flag, _, run = session
    flag.return_value = True
    register_native(http)
    http.get(FEATURES, body=requests.exceptions.ConnectionError("gateway down"))
    run.side_effect = [profile(), profile()]
    result = invoke()
    assert result.exit_code == 1
    assert "Could not recheck the SSH target with the workspace API" in result.output
    assert "tsh" not in result.output.split("Error:")[-1]
    assert [c.args[0][1] for c in run.call_args_list] == ["status", "status"]


def test_teleport_proxy_is_only_for_new_api_dev_pods(session):
    http, _, _, run = session
    result = invoke("--teleport-proxy", "proxy.example.com")
    assert result.exit_code == 2
    assert "only applies to Dev Pods on the new DevPod API" in result.output
    assert len(http.calls) == 0
    run.assert_not_called()

    with patch("leptonai.cli.pod.APIClient") as client:
        result = CliRunner().invoke(
            pod, ["ssh", "-n", "my-pod", "--teleport-proxy", "proxy.example.com"]
        )
    assert result.exit_code == 2
    assert "--teleport-proxy requires --transport teleport" in result.output
    client.assert_not_called()


def test_auth_option_requires_teleport_before_api_client_creation():
    with patch("leptonai.cli.pod.APIClient") as client:
        result = CliRunner().invoke(
            pod, ["ssh", "-n", "my-pod", "--teleport-auth", "SSO"]
        )
    assert result.exit_code == 2
    assert "requires --transport teleport" in result.output
    client.assert_not_called()


@pytest.mark.parametrize(
    "port, profile_url",
    [
        (443, "https://proxy.example.com"),
        (8443, "https://proxy.example.com:8443"),
    ],
)
def test_matching_proxy_port_reuses_profile(session, port, profile_url):
    http, _, _, run = session
    register(http, connection={**CONNECTION, "port": port})
    run.side_effect = [profile(profile_url=profile_url), completed()]
    result = invoke()
    assert result.exit_code == 0, result.output
    assert run.call_count == 2
    assert f"--proxy=proxy.example.com:{port}" in run.call_args.args[0]


def test_wrong_proxy_port_requires_login(session):
    http, _, _, run = session
    register(http)
    run.side_effect = [
        profile(profile_url="https://proxy.example.com:8443"),
        completed(),
        profile(),
        completed(),
    ]
    result = invoke()
    assert result.exit_code == 0, result.output
    assert run.call_args_list[1].args[0][1] == "login"


@pytest.mark.parametrize("during_login", [False, True])
def test_keyboard_interrupt_exits_130(session, during_login):
    http, _, _, run = session
    register(http)
    run.side_effect = [logged_out() if during_login else profile(), KeyboardInterrupt()]
    result = invoke()
    assert result.exit_code == 130


@pytest.mark.parametrize("args", [[], ["--transport", "ssh"]])
def test_direct_ssh_keeps_existing_behavior(args):
    pod_model = SimpleNamespace(
        metadata=SimpleNamespace(name="my-pod"),
        status=SimpleNamespace(
            state="Ready",
            container_port_status=[
                SimpleNamespace(container_port=2222, host_port=30022)
            ],
        ),
        model_dump=lambda: {},
    )
    client = SimpleNamespace(pod=SimpleNamespace(get=lambda _: pod_model))
    with (
        patch("leptonai.cli.pod.APIClient", return_value=client),
        patch(
            "leptonai.cli.pod._get_only_replica_public_ip", return_value="203.0.113.7"
        ),
        patch("leptonai.cli.pod.subprocess.run") as run,
        patch("leptonai.cli.pod.connect_teleport") as teleport,
    ):
        result = CliRunner().invoke(pod, ["ssh", "-n", "my-pod", *args])
    assert result.exit_code == 0, result.output
    assert run.call_args.args[0] == ["ssh", "-p", "30022", "root@203.0.113.7"]
    teleport.assert_not_called()
