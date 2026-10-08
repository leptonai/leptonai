from typing import Any
from unittest.mock import Mock

import pytest

from leptonai.api.v2.deployment import DeploymentAPI
from leptonai.api.v2.devpod import DevPodAPI, NewDevPodAPIUnsupported
from leptonai.api.v2.endpoint import EndpointAPI
from leptonai.api.v2.job import JobAPI
from leptonai.api.v2.pod import PodAPI
from leptonai.api.v2.raycluster import RayClusterAPI
from leptonai.api.v2.shell import ShellUnavailable, select_shell_replica


GATEWAY = "https://gateway.example.com/api/v2/workspaces/ws"


def replica(rid, reason=None, nested=True):
    item = {"metadata": {"id": rid}} if nested else {"id": rid}
    if reason is not None:
        item["status"] = {"readiness_issue": {"reason": reason}}
    return item


def test_the_only_running_replica_is_chosen():
    replicas = [
        replica("w-0", "Completed"),
        replica("w-1", "Ready"),
        replica("w-2", "Deleted"),
        replica("w-3", "Failed"),
        replica("w-4", "Terminated"),
    ]
    assert select_shell_replica(replicas, None, "job train") == "w-1"
    # A replica that is still starting has a container worth a shell.
    assert select_shell_replica([replica("w-0", "Starting")], None, "pod p") == "w-0"
    assert select_shell_replica([replica("w-0", nested=False)], None, "pod p") == "w-0"


def test_several_running_replicas_need_an_explicit_choice():
    replicas = [replica(f"w-{i}") for i in range(12)]
    with pytest.raises(ShellUnavailable) as error:
        select_shell_replica(replicas, None, "endpoint My-Endpoint")
    message = str(error.value)
    assert message.startswith("Endpoint My-Endpoint has 12 running replicas.")
    assert "--replica: w-0, w-1" in message and message.endswith(", ....")
    assert select_shell_replica(replicas, "w-7", "endpoint e") == "w-7"


@pytest.mark.parametrize(
    "replicas, requested, message",
    [
        ([], None, "has no running replicas"),
        ([replica("w-0", "Completed")], None, "has no running replicas"),
        ([replica("w-0")], "w-9", "does not belong to job j. Current replicas: w-0."),
        ([replica("w-0", "Failed")], "w-0", "has stopped"),
        ({"items": []}, None, "invalid replica list"),
        ([replica("w-0"), replica("w-0")], None, "duplicate replica IDs"),
        ([{"metadata": {}}], None, "invalid or duplicate"),
    ],
)
def test_unusable_replica_lists_explain_why(replicas, requested, message):
    with pytest.raises(ShellUnavailable, match=message.replace(".", r"\.")):
        select_shell_replica(replicas, requested, "job j")


class _Response:
    def __init__(self, payload: Any):
        self._payload = payload
        self.status_code = 200
        self.text = ""

    def json(self):
        return self._payload


@pytest.fixture
def opened(monkeypatch):
    connect = Mock(return_value=Mock())
    monkeypatch.setattr("websocket.create_connection", connect)

    def url():
        return connect.call_args.args[0]

    return url


def _client(payload: Any = None):
    client = Mock()
    client.url = GATEWAY
    client._header = {"Authorization": "Bearer t"}
    client._get.return_value = _Response(payload)
    return client


@pytest.mark.parametrize(
    "api_class, args, path",
    [
        (
            DeploymentAPI,
            ("ep a", "ep a-0"),
            "/deployments/ep%20a/replicas/ep%20a-0/shell",
        ),
        (EndpointAPI, ("ep", "ep-0"), "/endpoints/ep/replicas/ep-0/shell"),
        (PodAPI, ("pod", "pod-0"), "/deployments/pod/replicas/pod-0/shell"),
        (DevPodAPI, ("pod", None), "/devpods/pod/shell"),
        (JobAPI, ("train", "train-0"), "/jobs/train/replicas/train-0/shell"),
        (RayClusterAPI, ("rc", None), "/rayclusters/rc/shell"),
        (RayClusterAPI, ("rc", "rc-w-0"), "/rayclusters/rc/replicas/rc-w-0/shell"),
    ],
)
def test_shell_routes_match_the_dashboard_terminal(opened, api_class, args, path):
    api_class(_client()).shell_connection(*args)
    assert opened() == "wss://gateway.example.com/api/v2/workspaces/ws" + path


@pytest.mark.parametrize(
    "api_class, path, message",
    [
        (DeploymentAPI, "/deployments/ep/replicas", "Endpoint ep has no running"),
        (EndpointAPI, "/endpoints/ep/replicas", "Endpoint ep has no running"),
        (PodAPI, "/deployments/ep/replicas", "Pod ep has no running"),
    ],
)
def test_replica_shells_choose_from_the_workload_replicas(api_class, path, message):
    client = _client([replica("ep-0", "Ready"), replica("ep-1", "Deleted")])
    assert api_class(client).get_shell_replica("ep") == "ep-0"
    assert client._get.call_args.args == (path,)

    client._get.return_value = _Response([replica("ep-1", "Deleted")])
    with pytest.raises(ShellUnavailable, match=message):
        api_class(client).get_shell_replica("ep")


def test_job_shell_replicas_exclude_archived_runs():
    client = _client([replica("train-0")])
    assert JobAPI(client).get_shell_replica("train") == "train-0"
    assert client._get.call_args.args == ("/jobs/train/replicas",)
    assert client._get.call_args.kwargs == {"params": {"job_query_mode": "alive_only"}}


def test_ray_cluster_shell_defaults_to_the_head_without_a_lookup():
    client = _client([replica("rc-head"), replica("rc-w-0", "Deleted")])
    api = RayClusterAPI(client)
    assert api.get_shell_replica("rc") is None
    client._get.assert_not_called()
    assert api.get_shell_replica("rc", "rc-head") == "rc-head"
    with pytest.raises(ShellUnavailable, match="has stopped"):
        api.get_shell_replica("rc", "rc-w-0")


@pytest.mark.parametrize(
    "spec, status",
    [
        ({"stopped": True}, {"state": "Ready"}),
        ({}, {"state": "Starting"}),
    ],
)
def test_new_api_dev_pod_shell_needs_a_running_pod(spec, status):
    body = {"metadata": {"name": "pod"}, "spec": spec, "status": status}
    with pytest.raises(NewDevPodAPIUnsupported, match="not Ready"):
        DevPodAPI(_client(body)).get_shell_replica("pod")


def test_new_api_dev_pod_shell_has_no_replica_choice():
    client = _client({"metadata": {"name": "pod"}, "status": {"state": "Ready"}})
    api = DevPodAPI(client)
    assert api.get_shell_replica("pod") is None
    with pytest.raises(NewDevPodAPIUnsupported, match="--replica"):
        api.get_shell_replica("pod", "pod-0")
