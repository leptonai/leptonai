from typing import Any
from unittest.mock import Mock

import pytest

from leptonai.api.v2.deployment import DeploymentAPI
from leptonai.api.v2.devpod import DevPodAPI, NewDevPodAPIUnsupported
from leptonai.api.v2.endpoint import EndpointAPI
from leptonai.api.v2.job import JobAPI
from leptonai.api.v2.pod import PodAPI
from leptonai.api.v2.raycluster import RayClusterAPI
from leptonai.api.v2.shell import (
    ShellUnavailable,
    is_lepton_system_image,
    select_shell_replica,
)


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
    "api_class, path",
    [
        (DeploymentAPI, "/deployments/ep/replicas"),
        (EndpointAPI, "/endpoints/ep/replicas"),
    ],
)
def test_endpoint_shells_choose_from_the_running_replicas(api_class, path):
    client = _client([replica("ep-0", "Ready"), replica("ep-1", "Deleted")])
    assert api_class(client).get_shell_replica("ep") == "ep-0"
    assert client._get.call_args.args == (path,)

    client._get.return_value = _Response([replica("ep-1", "Terminated")])
    with pytest.raises(ShellUnavailable, match="Endpoint ep has no running"):
        api_class(client).get_shell_replica("ep")


def _reads(client, *payloads):
    client._get.side_effect = [_Response(payload) for payload in payloads]
    return client


def _created(rid, created_at, reason="Ready"):
    item = replica(rid, reason)
    item["metadata"]["created_at"] = created_at
    return item


def test_pod_shell_uses_the_newest_replica_of_a_ready_pod():
    # As the dashboard's Pod card does while a restart briefly shows two.
    pod = {"status": {"state": "Not Ready", "phase": "Ready"}}
    replicas = [_created("pod-old", 1), _created("pod-new", 2)]
    client = _reads(_client(), pod, replicas)
    assert PodAPI(client).get_shell_replica("pod") == "pod-new"
    assert [c.args for c in client._get.call_args_list] == [
        ("/deployments/pod",),
        ("/deployments/pod/replicas",),
    ]

    client = _reads(_client(), pod, [_created("pod-0", 1, "Failed")])
    with pytest.raises(ShellUnavailable, match="has stopped"):
        PodAPI(client).get_shell_replica("pod")

    client = _reads(_client(), pod, replicas)
    assert PodAPI(client).get_shell_replica("pod", "pod-old") == "pod-old"


@pytest.mark.parametrize(
    "status", [{"state": "Ready", "phase": "Stopped"}, {"state": "Not Ready"}, None]
)
def test_pod_shell_needs_a_ready_pod(status):
    client = _reads(_client(), {"status": status}, [replica("pod-0")])
    with pytest.raises(ShellUnavailable, match="is not Ready"):
        PodAPI(client).get_shell_replica("pod")
    assert client._get.call_count == 1


def test_job_shell_reads_live_replicas():
    job = {"spec": {"container": {"image": "nvcr.io/nvidia/pytorch:24.01"}}}
    client = _reads(_client(), job, [replica("train-0")])
    assert JobAPI(client).get_shell_replica("train") == "train-0"
    alive = {"params": {"job_query_mode": "alive_only"}}
    assert [(c.args, c.kwargs) for c in client._get.call_args_list] == [
        (("/jobs/train",), alive),
        (("/jobs/train/replicas",), alive),
    ]


@pytest.mark.parametrize(
    "job, message",
    [
        ({"status": {"state": "Archived"}}, "is archived"),
        ({"spec": {"container": {"image": "leptonai/l3m:0.3"}}}, "system image"),
        ({"spec": {"container": {"image": "leptonai/lep-tuner"}}}, "system image"),
        ({"spec": {"container": {"image": "default/lepton:tuna-v2"}}}, "system image"),
    ],
)
def test_job_shell_is_unavailable_where_the_dashboard_hides_it(job, message):
    client = _reads(_client(), job)
    with pytest.raises(ShellUnavailable, match=message):
        JobAPI(client).get_shell_replica("train")


@pytest.mark.parametrize(
    "image, system",
    [
        ("leptonai/l3m", True),
        ("docker.io/leptonai/l3m:1.2.3", True),
        ("registry.example.com/team/lepton:tuna", False),
        ("leptonai/l3m-custom", False),
        ("myorg/leptonai/l3m", False),
        (None, False),
    ],
)
def test_system_images_match_the_dashboard_patterns(image, system):
    assert is_lepton_system_image(image) is system


@pytest.mark.parametrize("state", ["Stopped", "Stopping", "", None])
def test_ray_head_shell_needs_a_running_cluster(state):
    client = _reads(_client(), {"status": {"state": state}})
    with pytest.raises(ShellUnavailable, match="head shell needs a running cluster"):
        RayClusterAPI(client).get_shell_replica("rc")


def test_ray_cluster_shell_defaults_to_the_head():
    client = _reads(_client(), {"status": {"state": "Scaling"}})
    assert RayClusterAPI(client).get_shell_replica("rc") is None
    assert client._get.call_args.args == ("/rayclusters/rc",)

    replicas = [
        replica("rc-head"),
        replica("rc-w-0", "Deleted"),
        replica("rc-w-1", "Terminated"),
    ]
    api = RayClusterAPI(_client(replicas))
    assert api.get_shell_replica("rc", "rc-head") == "rc-head"
    # The dashboard's Ray replica table leaves Terminated replicas enabled.
    assert api.get_shell_replica("rc", "rc-w-1") == "rc-w-1"
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
    with pytest.raises(ShellUnavailable, match="not Ready"):
        DevPodAPI(_client(body)).get_shell_replica("pod")


def test_new_api_dev_pod_shell_has_no_replica_choice():
    client = _client({"metadata": {"name": "pod"}, "status": {"state": "Ready"}})
    api = DevPodAPI(client)
    assert api.get_shell_replica("pod") is None
    with pytest.raises(NewDevPodAPIUnsupported, match="--replica"):
        api.get_shell_replica("pod", "pod-0")
