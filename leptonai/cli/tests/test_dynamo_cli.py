"""CLI tests for `lep dynamo`, driven through CliRunner with a fake API client."""

import json
import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

import pytest
from click.testing import CliRunner

from leptonai.api.v2.api_resource import ClientError
from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.dedicated_node_group import (
    DedicatedNodeGroup,
    DedicatedNodeGroupSpec,
    DedicatedNodeGroupStatus,
)
from leptonai.api.v2.types.dynamo import (
    DYNAMO_WORKER_ROLE_LABEL_KEY,
    DynamoHistoryItem,
    DynamoMonitoringStatusResponse,
    DynamoReplica,
    DynamoReplicaDeleteResponse,
    DynamoReplicaLogResponse,
    DynamoServiceReplicasResponse,
    DynamoServiceResponse,
    DynamoServiceRestartResponse,
    DynamoServicesResponse,
    LeptonDynamoGraphDeployment,
    LeptonDynamoGraphDeploymentUserSpec,
)
from leptonai.api.v2.types.shape import Shape, ShapeSpec
from leptonai.cli import lep as cli
from leptonai.cli.dynamo import console as dynamo_console

VLLM_IMAGE = "nvcr.io/nvidia/ai-dynamo/vllm-runtime:1.3.1"


class _FakeResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


def _not_found(what):
    return ClientError(_FakeResponse(404, f'{{"message": "{what} not found"}}'))


def _service_spec(component_type, shape, replicas, command, working_dir, labels=None):
    return {
        "component_type": component_type,
        "resource_shape": shape,
        "min_replicas": replicas,
        "max_replicas": replicas,
        "affinity": {"allowed_dedicated_node_groups": ["ng-1"]},
        "extra_pod_spec": {
            "main_container": {
                "image": VLLM_IMAGE,
                "working_dir": working_dir,
                "command": ["/bin/sh", "-c", command],
            }
        },
        "extra_pod_metadata": {"annotations": {}, "labels": labels or {}},
    }


def _deployment(name, services=None, state="Ready", created_by="alice"):
    if services is None:
        services = {
            "frontend": _service_spec(
                "frontend", "cpu.small", 1, "python3 -m dynamo.frontend", "/workspace"
            ),
            "worker": _service_spec(
                "worker",
                "gpu.a100-1",
                2,
                "python3 -m dynamo.vllm --model Qwen/Qwen3-0.6B",
                "/workspace/examples/backends/vllm",
            ),
        }
    return {
        "metadata": {
            "id": name,
            "name": name,
            "created_at": 1717000000000,
            "created_by": created_by,
            "visibility": "private",
        },
        "spec": {
            "dynamo_version": "1.3.1",
            "backend_framework": "vllm",
            "ingress_enabled": True,
            "envs": [{"name": "MODEL", "value": "Qwen/Qwen3-0.6B"}],
            "services": services,
        },
        "status": {
            "state": state,
            "services": {
                svc: {
                    "state": "Ready",
                    "ready_replicas": 1,
                    "desired_replicas": spec["min_replicas"],
                }
                for svc, spec in services.items()
            },
            "endpoint": {
                "external_endpoint": f"https://{name}.example.com",
                "internal_endpoint": "http://internal",
            },
        },
    }


def _replica(rid, reason="Ready", node="node-1"):
    return {
        "metadata": {"id": rid, "name": rid, "created_at": 1717000000000},
        "id": rid,
        "status": {
            "readiness_issue": {
                "reason": reason,
                "message": "",
                "creationTimestamp": "2024-01-01T00:00:00Z",
            },
            "node": {"name": node, "id": "n-1", "node_group_id": "ng-1"},
        },
    }


class FakeDynamoAPI:
    def __init__(self):
        self.deployments = {}
        self.service_infos = {}
        self.service_details = {}
        self.replicas = {}
        self.logs = {}
        self.metrics = {}
        self.metrics_404 = set()
        self.history_items = []
        self.monitoring = {
            "overall_health": "degraded",
            "total_services": 2,
            "healthy_services": 1,
            "services": {"frontend": "healthy", "worker": "unhealthy"},
        }
        self.calls = []
        self.created = None
        self.updated = None

    def add_deployment(self, payload):
        dep = LeptonDynamoGraphDeployment(**payload)
        self.deployments[payload["metadata"]["name"]] = dep
        return dep

    def _dep(self, name):
        if name not in self.deployments:
            raise _not_found(name)
        return self.deployments[name]

    def safe_json(self, obj):
        return obj.model_dump(mode="json", exclude_none=True, by_alias=True)

    def list_all(self):
        return list(self.deployments.values())

    def get(self, name):
        return self._dep(name)

    def create(self, dep):
        self.created = dep
        return dep

    def update(self, name, patch, dryrun=False):
        self._dep(name)
        self.updated = (name, patch, dryrun)
        return self.deployments[name]

    def delete(self, name):
        self._dep(name)
        self.calls.append(("delete", name))
        return True

    def list_services(self, name):
        self._dep(name)
        return DynamoServicesResponse(services=self.service_infos.get(name, {}))

    def get_service(self, name, service):
        self._dep(name)
        detail = self.service_details.get((name, service))
        if detail is None:
            raise _not_found(service)
        return DynamoServiceResponse(**detail)

    def restart_service(self, name, service):
        self.calls.append(("restart", name, service))
        return DynamoServiceRestartResponse(
            message="Restart initiated", service=service, deleted_pods=["pod-1"]
        )

    def list_service_replicas(self, name, service):
        self._dep(name)
        return DynamoServiceReplicasResponse(
            service=service,
            replicas=[
                DynamoReplica(**r) for r in self.replicas.get((name, service), [])
            ],
        )

    def list_replicas(self, name, service=None):
        self._dep(name)
        items = []
        for (dep_name, svc), replicas in self.replicas.items():
            if dep_name == name and (service is None or svc == service):
                items.extend(DynamoReplica(**r) for r in replicas)
        return items

    def get_replica_log(self, name, replica, service=None, tail=None, timestamps=False):
        self.calls.append(("log", name, replica, service, tail, timestamps))
        return DynamoReplicaLogResponse(
            deployment=name,
            service=service,
            replica=replica,
            logs=self.logs.get(replica, ""),
        )

    def delete_replica(self, name, replica, service=None):
        self.calls.append(("delete_replica", name, replica, service))
        return DynamoReplicaDeleteResponse(
            message="deleting", replica=replica, service=service
        )

    def get_monitoring_status(self, name):
        return DynamoMonitoringStatusResponse(**self.monitoring)

    def get_history(self, name):
        return [DynamoHistoryItem(**item) for item in self.history_items]

    def get_metric(self, name, metric, window=None):
        self.calls.append(("metric", name, metric, window))
        if metric in self.metrics_404:
            raise _not_found(metric)
        return self.metrics.get(metric, [])

    def get_replica_metric(self, name, replica, metric):
        self.calls.append(("replica_metric", name, replica, metric))
        if metric in self.metrics_404:
            raise _not_found(metric)
        return self.metrics.get(metric, [])


class FakeNodeGroupAPI:
    def list_all(self):
        return [
            DedicatedNodeGroup(
                metadata=Metadata(id="ng-1", name="my-ng"),
                spec=DedicatedNodeGroupSpec(),
                status=DedicatedNodeGroupStatus(),
            )
        ]


class FakeShapesAPI:
    def list_shapes(self, node_group=None, purpose=None):
        return [
            Shape(
                metadata=Metadata(id="gpu.h100-8", name="gpu.h100-8"),
                spec=ShapeSpec(name="gpu.h100-8", accelerator_num=8),
            )
        ]


class FakeAPIClient:
    dynamo_api = None

    def __init__(self, *args, **kwargs):
        self.dynamo = FakeAPIClient.dynamo_api
        self.nodegroup = FakeNodeGroupAPI()
        self.shapes = FakeShapesAPI()


@pytest.fixture
def fake(monkeypatch):
    api = FakeDynamoAPI()
    api.add_deployment(_deployment("my-dynamo"))
    api.add_deployment(
        _deployment(
            "solo",
            services={
                "frontend": _service_spec(
                    "frontend",
                    "cpu.small",
                    1,
                    "python3 -m dynamo.frontend",
                    "/workspace",
                )
            },
            state="Starting",
            created_by="bob",
        )
    )
    api.service_infos["my-dynamo"] = {
        "frontend": {
            "component_type": "frontend",
            "min_replicas": 1,
            "desired_replicas": 1,
            "ready_replicas": 1,
            "total_pods": 1,
            "is_multinode": False,
        },
        "worker": {
            "component_type": "worker",
            "min_replicas": 2,
            "desired_replicas": 2,
            "ready_replicas": 1,
            "total_pods": 4,
            "is_multinode": True,
            "node_count": 2,
        },
    }
    worker_spec = api.deployments["my-dynamo"].spec.services["worker"]
    api.service_details[("my-dynamo", "worker")] = {
        "name": "worker",
        "component_type": "worker",
        "resource_shape": "gpu.a100-1",
        "min_replicas": 2,
        "ready_replicas": 1,
        "desired_replicas": 2,
        "is_multinode": True,
        "node_count": 2,
        "spec": worker_spec.model_dump(mode="json", exclude_none=True, by_alias=True),
        "status": {
            "state": "Starting",
            "phase": "Running",
            "health": "degraded",
            "replicas": {"desired": 2, "ready": 1, "running": 2, "total_pods": 4},
            "conditions": [{
                "type": "Available",
                "status": "False",
                "reason": "Pending",
                "message": "warming up",
            }],
        },
    }
    api.service_details[("my-dynamo", "idle")] = {
        "name": "idle",
        "component_type": "worker",
        "min_replicas": 0,
        "spec": {"component_type": "worker", "min_replicas": 0},
    }
    api.replicas[("my-dynamo", "frontend")] = [_replica("frontend-abc")]
    api.replicas[("my-dynamo", "worker")] = [_replica("worker-xyz", "InProgress")]
    api.logs["frontend-abc"] = "line1\nline2\n"
    api.logs["worker-xyz"] = "worker log\n"
    api.history_items = [
        {"timestamp": 1717000000000, "operation": "create", "description": "created"}
    ]
    api.metrics = {
        "GPUUtilAvg": [{
            "metric": {"name": "GPUUtilAvg", "device": "0"},
            "values": [[1717000000, "0.25"], [1717000060, "0.75"]],
        }],
        "GPUUtil": [{
            "metric": {"name": "GPUUtil"},
            "values": [[1717000000, "0.5"], [1717000060, None]],
        }],
    }
    api.metrics_404 = {"GPUTempAvg", "GPUPowerConsumption"}

    FakeAPIClient.dynamo_api = api
    monkeypatch.setattr("leptonai.cli.dynamo.APIClient", FakeAPIClient)
    monkeypatch.setattr(dynamo_console, "width", 240)
    return api


def run(*args, input=None):
    return CliRunner().invoke(cli, ["dynamo", *args], input=input)


# ---------------------------------------------------------------------------
# read commands
# ---------------------------------------------------------------------------


def test_list_renders_and_filters(fake):
    result = run("list")
    assert result.exit_code == 0, result.output
    assert "my-dynamo" in result.output
    assert "solo" in result.output
    assert "vllm" in result.output
    assert "aggregated" in result.output
    assert "frontend:" in result.output and "cpu.small" in result.output
    assert "ng-1" in result.output

    result = run("list", "--state", "ready")
    assert "my-dynamo" in result.output and "solo" not in result.output

    result = run("list", "--created-by", "bob")
    assert "solo" in result.output and "my-dynamo" not in result.output

    result = run("list", "-n", "nomatch")
    assert "No Dynamo deployments found" in result.output


def test_get_prints_json_and_saves_spec(fake, tmp_path):
    result = run("get", "-n", "my-dynamo", "-p", str(tmp_path))
    assert result.exit_code == 0, result.output
    json_text = result.output.split("Dynamo deployment spec saved")[0]
    payload = json.loads(json_text)
    assert payload["metadata"]["name"] == "my-dynamo"
    assert "worker" in payload["spec"]["services"]

    saved = tmp_path / "dynamo-spec-my-dynamo.json"
    assert saved.exists()
    spec = LeptonDynamoGraphDeploymentUserSpec.model_validate_json(saved.read_text())
    assert set(spec.services) == {"frontend", "worker"}

    result = run("get", "-n", "missing")
    assert result.exit_code == 1
    assert "404" in result.output


def test_status_shows_summary_services_health_and_replicas(fake):
    result = run("status", "-n", "my-dynamo")
    assert result.exit_code == 0, result.output
    assert "Ready" in result.output
    assert "Framework:   vllm" in result.output
    assert "Mode:        aggregated" in result.output
    assert "https://my-dynamo.example.com" in result.output
    assert "Global envs: MODEL" in result.output
    assert "degraded" in result.output
    assert "1/2 services healthy" in result.output
    assert "2 nodes" in result.output
    assert "frontend-abc" in result.output and "worker-xyz" in result.output
    assert "InProgress" in result.output
    assert "1 out of 2 replicas ready" in result.output


def test_service_list_and_get(fake):
    result = run("service", "list", "-n", "my-dynamo")
    assert result.exit_code == 0, result.output
    assert "frontend" in result.output and "worker" in result.output
    assert "2 nodes" in result.output

    result = run("service", "get", "-n", "my-dynamo", "-s", "worker")
    assert result.exit_code == 0, result.output
    assert "Shape:        gpu.a100-1" in result.output
    assert "Multinode:    2 nodes" in result.output
    assert "python3 -m dynamo.vllm --model Qwen/Qwen3-0.6B" in result.output
    assert "ready 1 / desired 2" in result.output
    assert "Available" in result.output and "warming up" in result.output

    result = run("service", "get", "-n", "my-dynamo", "-s", "nope")
    assert result.exit_code == 1
    assert "404" in result.output


def test_replicas_filters(fake):
    result = run("replica", "list", "-n", "my-dynamo")
    assert result.exit_code == 0, result.output
    assert "frontend-abc" in result.output and "worker-xyz" in result.output
    assert "node-1" in result.output

    result = run("replica", "list", "-n", "my-dynamo", "-s", "worker")
    assert "worker-xyz" in result.output and "frontend-abc" not in result.output

    result = run("replica", "list", "-n", "my-dynamo", "--state", "ready")
    assert "frontend-abc" in result.output and "worker-xyz" not in result.output

    result = run("replica", "list", "-n", "my-dynamo", "-s", "nope")
    assert result.exit_code == 1
    assert "Available services: frontend, worker" in result.output


def test_log_selects_first_ready_replica_and_passes_options(fake):
    result = run("replica", "log", "-n", "my-dynamo")
    assert result.exit_code == 0, result.output
    assert "selected replica frontend-abc of service frontend" in result.output
    assert "line1" in result.output and "line2" in result.output
    assert fake.calls[-1] == (
        "log",
        "my-dynamo",
        "frontend-abc",
        "frontend",
        None,
        False,
    )

    result = run(
        "replica",
        "log",
        "-n",
        "my-dynamo",
        "-s",
        "worker",
        "--tail",
        "20",
        "--timestamps",
    )
    assert result.exit_code == 0, result.output
    assert "worker log" in result.output
    assert fake.calls[-1] == ("log", "my-dynamo", "worker-xyz", "worker", 20, True)

    result = run("replica", "log", "-n", "my-dynamo", "-r", "frontend-abc")
    assert result.exit_code == 0, result.output
    assert fake.calls[-1] == ("log", "my-dynamo", "frontend-abc", None, None, False)

    result = run("replica", "log", "-n", "my-dynamo", "-s", "nope")
    assert result.exit_code == 1
    assert "Available services" in result.output


def test_log_saves_to_path(fake, tmp_path):
    result = run(
        "replica",
        "log",
        "-n",
        "my-dynamo",
        "-r",
        "frontend-abc",
        "-p",
        str(tmp_path),
    )
    assert result.exit_code == 0, result.output
    saved = tmp_path / "dynamo-log-my-dynamo-frontend-abc.txt"
    assert saved.read_text() == "line1\nline2\n"


def test_restart_confirmation_and_guards(fake):
    result = run("service", "restart", "-n", "my-dynamo", "-s", "worker", input="n\n")
    assert result.exit_code == 0, result.output
    assert "Aborted" in result.output
    assert not [c for c in fake.calls if c[0] == "restart"]

    result = run("service", "restart", "-n", "my-dynamo", "-s", "worker", "-y")
    assert result.exit_code == 0, result.output
    assert "Restart request has been sent" in result.output
    assert "pod-1" in result.output
    assert ("restart", "my-dynamo", "worker") in fake.calls

    result = run("service", "restart", "-n", "my-dynamo", "-s", "idle", "-y")
    assert result.exit_code == 1
    assert "nothing to restart" in result.output


def test_remove_and_remove_replica(fake):
    result = run("remove", "-n", "my-dynamo", input="n\n")
    assert result.exit_code == 0
    assert ("delete", "my-dynamo") not in fake.calls

    result = run("remove", "-n", "my-dynamo", "-y")
    assert result.exit_code == 0, result.output
    assert "Deletion request has been sent" in result.output
    assert ("delete", "my-dynamo") in fake.calls

    result = run(
        "replica",
        "remove",
        "-n",
        "my-dynamo",
        "-r",
        "worker-xyz",
        "-s",
        "worker",
        "-y",
    )
    assert result.exit_code == 0, result.output
    assert ("delete_replica", "my-dynamo", "worker-xyz", "worker") in fake.calls
    assert "worker-xyz" in result.output


def test_history_and_metrics(fake):
    result = run("history", "-n", "my-dynamo")
    assert result.exit_code == 0, result.output
    assert "create" in result.output and "created" in result.output

    result = run("metrics", "-n", "my-dynamo", "--window", "6")
    assert result.exit_code == 0, result.output
    assert "GPUUtilAvg" in result.output
    assert "0.75" in result.output  # latest
    assert "GPUTempAvg" not in result.output  # 404 panels are hidden
    assert "no data" in result.output  # metrics without series
    assert ("metric", "my-dynamo", "GPUUtilAvg", 6) in fake.calls

    result = run(
        "replica",
        "metrics",
        "-n",
        "my-dynamo",
        "-r",
        "worker-xyz",
        "-m",
        "GPUUtil",
    )
    assert result.exit_code == 0, result.output
    assert ("replica_metric", "my-dynamo", "worker-xyz", "GPUUtil") in fake.calls
    assert "0.5" in result.output


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def _created_spec(fake):
    assert fake.created is not None
    return fake.created.spec


def test_create_single_frontend(fake):
    result = run(
        "create",
        "-n",
        "new-dyn",
        "-svc",
        "frontend",
        "--resource-shape",
        "cpu.small",
        "--node-group",
        "my-ng",
    )
    assert result.exit_code == 0, result.output
    assert "created successfully" in result.output
    assert fake.created.metadata.name == "new-dyn"
    spec = _created_spec(fake)
    assert spec.backend_framework == "vllm"
    assert spec.dynamo_version == "1.3.1"
    assert spec.ingress_enabled is True
    assert list(spec.services) == ["frontend"]
    frontend = spec.services["frontend"]
    assert frontend.affinity.allowed_dedicated_node_groups == [
        "ng-1"
    ]  # resolved by name
    assert frontend.min_replicas == 1
    assert frontend.extra_pod_spec.main_container.image == VLLM_IMAGE
    assert frontend.extra_pod_spec.main_container.command == [
        "/bin/sh",
        "-c",
        "python3 -m dynamo.frontend",
    ]


def test_create_aggregated_worker_with_envs_and_options(fake):
    result = run(
        "create",
        "-n",
        "agg-test",
        "-e",
        "MODEL_NAME=Qwen/Qwen3-0.6B",
        "-s",
        "HF_TOKEN=my-secret",
        "--no-ingress",
        "--ingress-timeout",
        "600",
        "--visibility",
        "private",
        "-svc",
        "frontend",
        "--resource-shape",
        "cpu.small",
        "--node-group",
        "ng-1",
        "-svc",
        "worker",
        "--resource-shape",
        "gpu.a100-1",
        "--replicas",
        "2",
        "-e",
        "TP=1",
        "--mount",
        "/data:/mnt/data:node-nfs:my-nfs",
        "--annotation",
        "app=dynamo",
        "--label",
        "tier=compute",
    )
    assert result.exit_code == 0, result.output
    spec = _created_spec(fake)
    assert fake.created.metadata.visibility.value == "private"
    assert spec.ingress_enabled is False
    assert spec.ingress_timeout_seconds == 600
    assert [e.name for e in spec.envs] == ["MODEL_NAME", "HF_TOKEN"]
    assert spec.envs[1].value_from.secret_name_ref == "my-secret"

    worker = spec.services["worker"]
    assert worker.min_replicas == 2
    assert worker.affinity.allowed_dedicated_node_groups == ["ng-1"]  # inherited
    assert [e.name for e in worker.envs] == ["TP"]
    assert worker.mounts[0].from_ == "node-nfs:my-nfs"
    assert worker.extra_pod_metadata.annotations == {"app": "dynamo"}
    assert worker.extra_pod_metadata.labels == {"tier": "compute"}
    assert (
        worker.extra_pod_spec.main_container.working_dir
        == "/workspace/examples/backends/vllm"
    )


def test_create_disaggregated_sglang_with_multinode(fake):
    result = run(
        "create",
        "-n",
        "disagg-test",
        "--framework",
        "sglang",
        "--serving-mode",
        "disaggregated",
        "-svc",
        "frontend",
        "--resource-shape",
        "cpu.small",
        "--node-group",
        "my-ng",
        "-svc",
        "prefill-worker",
        "--resource-shape",
        "gpu.h100-8",
        "--node-count",
        "2",
        "-svc",
        "decode-worker",
        "--resource-shape",
        "gpu.h100-8",
    )
    assert result.exit_code == 0, result.output
    spec = _created_spec(fake)
    assert set(spec.services) == {"frontend", "prefill-worker", "decode-worker"}
    prefill = spec.services["prefill-worker"]
    decode = spec.services["decode-worker"]
    assert prefill.extra_pod_metadata.labels == {
        DYNAMO_WORKER_ROLE_LABEL_KEY: "prefill"
    }
    assert decode.extra_pod_metadata.labels == {DYNAMO_WORKER_ROLE_LABEL_KEY: "decode"}
    assert prefill.multinode.node_count == 2
    # gpu_count 8 (from the shapes API) x 2 nodes
    assert "--tp-size 16" in prefill.extra_pod_spec.main_container.command[2]
    assert decode.multinode is None
    assert prefill.extra_pod_spec.main_container.image.endswith("sglang-runtime:1.3.1")


def test_create_rejections(fake):
    frontend = [
        "-svc",
        "frontend",
        "--resource-shape",
        "cpu.small",
        "--node-group",
        "my-ng",
    ]

    result = run("create", "-n", "x", "--serving-mode", "disaggregated", *frontend)
    assert result.exit_code == 1 and "not supported for vLLM" in result.output

    result = run(
        "create",
        "-n",
        "x",
        "--framework",
        "sglang",
        "--serving-mode",
        "disaggregated",
        *frontend,
        "-svc",
        "worker",
        "--resource-shape",
        "gpu.a10",
    )
    assert (
        result.exit_code == 1 and "not available in disaggregated mode" in result.output
    )

    result = run("create", "-n", "x", "-svc", "worker", "--resource-shape", "gpu.a10")
    assert result.exit_code == 1 and "frontend service is required" in result.output

    result = run(
        "create",
        "-n",
        "x",
        *frontend,
        "-svc",
        "worker",
        "--resource-shape",
        "gpu.a10",
        "--node-count",
        "2",
    )
    assert result.exit_code == 1 and "only supported for SGLang" in result.output

    result = run(
        "create",
        "-n",
        "x",
        "-svc",
        "frontend",
        "--resource-shape",
        "cpu.small",
        "--node-group",
        "nope",
    )
    assert result.exit_code == 1 and "Invalid node group" in result.output

    result = run("create", "-n", "Bad_Name", *frontend)
    assert result.exit_code == 1 and "Name must consist" in result.output

    result = run("create", "-n", "x", "-svc", "--resource-shape", "cpu.small")
    assert result.exit_code == 2 and "requires a value" in result.output

    result = run("create", "-n", "x", "--resource-shape", "cpu.small")
    assert result.exit_code == 2 and "must follow" in result.output

    result = run(
        "create",
        "-n",
        "x",
        *frontend,
        "-svc",
        "worker",
        "--resource-shape",
        "gpu.a10",
        "--replicas",
        "two",
    )
    assert result.exit_code == 2 and "expects an integer" in result.output

    assert fake.created is None


def test_create_dry_run_and_image_warning(fake):
    result = run(
        "create",
        "-n",
        "dry",
        "--dry-run",
        "-svc",
        "frontend",
        "--resource-shape",
        "cpu.small",
        "--node-group",
        "my-ng",
        "--image",
        "myregistry/custom:1",
    )
    assert result.exit_code == 0, result.output
    assert fake.created is None
    assert "Warning" in result.output and "official runtime image" in result.output
    payload = (
        json.loads(result.output.split("Warning")[0])
        if result.output.startswith("{")
        else None
    )
    assert payload is None or payload["metadata"]["name"] == "dry"
    assert '"image": "myregistry/custom:1"' in result.output


def test_create_from_spec_file_with_overrides(fake, tmp_path):
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(
        fake.deployments["my-dynamo"].spec.model_dump_json(
            exclude_none=True, by_alias=True
        )
    )
    result = run(
        "create",
        "-n",
        "from-file",
        "-f",
        str(spec_file),
        "-svc",
        "worker",
        "--replicas",
        "3",
    )
    assert result.exit_code == 0, result.output
    spec = _created_spec(fake)
    assert set(spec.services) == {"frontend", "worker"}
    assert spec.services["worker"].min_replicas == 3
    assert spec.services["worker"].resource_shape == "gpu.a100-1"
    assert spec.services["frontend"].affinity.allowed_dedicated_node_groups == ["ng-1"]
    assert spec.envs[0].name == "MODEL"


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def test_update_replicas_builds_minimal_patch(fake):
    result = run("update", "-n", "my-dynamo", "-svc", "worker", "--replicas", "4", "-y")
    assert result.exit_code == 0, result.output
    name, patch, dryrun = fake.updated
    assert (name, dryrun) == ("my-dynamo", False)
    assert patch == {
        "spec": {"services": {"worker": {"min_replicas": 4, "max_replicas": 4}}}
    }
    assert "updated successfully" in result.output


def test_update_remove_service(fake):
    result = run("update", "-n", "my-dynamo", "-svc", "worker", "--remove", "-y")
    assert result.exit_code == 0, result.output
    assert fake.updated[1] == {"spec": {"services": {"worker": None}}}

    result = run("update", "-n", "my-dynamo", "-svc", "frontend", "--remove", "-y")
    assert (
        result.exit_code == 1 and "frontend service cannot be removed" in result.output
    )


def test_update_no_changes_and_global_flags(fake):
    result = run("update", "-n", "my-dynamo")
    assert result.exit_code == 0, result.output
    assert "No changes detected" in result.output
    assert fake.updated is None

    result = run(
        "update", "-n", "my-dynamo", "--no-ingress", "--display-name", "hi", "-e", "A=1"
    )
    assert result.exit_code == 0, result.output
    assert fake.updated[1] == {
        "spec": {
            "ingress_enabled": False,
            "display_name": "hi",
            "envs": [{"name": "A", "value": "1"}],
        }
    }


def test_update_service_change_requires_confirmation(fake):
    result = run(
        "update", "-n", "my-dynamo", "-svc", "worker", "--replicas", "4", input="n\n"
    )
    assert result.exit_code == 0, result.output
    assert "Aborted" in result.output
    assert fake.updated is None


def test_update_dryrun_and_raw_patch_file(fake, tmp_path):
    patch_file = tmp_path / "patch.json"
    patch_file.write_text(
        json.dumps(
            {"spec": {"routing_policy": {"enable_header_based_replica_routing": True}}}
        )
    )
    result = run(
        "update",
        "-n",
        "my-dynamo",
        "--dryrun",
        "-f",
        str(patch_file),
        "-svc",
        "worker",
        "--command",
        "python3 -m dynamo.vllm --model Qwen/Qwen3-8B",
    )
    assert result.exit_code == 0, result.output
    name, patch, dryrun = fake.updated
    assert dryrun is True
    assert patch["spec"]["routing_policy"] == {
        "enable_header_based_replica_routing": True
    }
    assert patch["spec"]["services"]["worker"] == {
        "extra_pod_spec": {
            "main_container": {
                "command": [
                    "/bin/sh",
                    "-c",
                    "python3 -m dynamo.vllm --model Qwen/Qwen3-8B",
                ]
            }
        }
    }
    assert "dry run" in result.output


def test_update_guards(fake):
    result = run(
        "update", "-n", "my-dynamo", "-svc", "worker", "--node-count", "2", "-y"
    )
    assert (
        result.exit_code == 1 and "cannot add multinode configuration" in result.output
    )

    result = run(
        "update", "-n", "my-dynamo", "-svc", "worker", "--node-group", "my-ng", "-y"
    )
    assert result.exit_code == 1 and "synchronized with the frontend" in result.output

    result = run(
        "update",
        "-n",
        "my-dynamo",
        "-svc",
        "prefill-worker",
        "--resource-shape",
        "gpu.a10",
        "-y",
    )
    assert result.exit_code == 1 and "not available in aggregated mode" in result.output

    result = run(
        "update",
        "-n",
        "my-dynamo",
        "-svc",
        "planner",
        "--resource-shape",
        "gpu.a10",
        "-y",
    )
    assert result.exit_code == 1 and "Unknown Dynamo service" in result.output

    result = run("update", "-n", "my-dynamo", "--ingress-timeout", "10")
    assert result.exit_code == 1 and "ingress_timeout_seconds" in result.output
    assert fake.updated is None


def test_update_clear_working_dir_and_add_service(fake):
    result = run(
        "update", "-n", "my-dynamo", "-svc", "worker", "--clear-working-dir", "-y"
    )
    assert result.exit_code == 0, result.output
    assert fake.updated[1] == {
        "spec": {
            "services": {
                "worker": {"extra_pod_spec": {"main_container": {"working_dir": None}}}
            }
        }
    }

    result = run(
        "update", "-n", "solo", "-svc", "worker", "--resource-shape", "gpu.a10", "-y"
    )
    assert result.exit_code == 0, result.output
    worker_patch = fake.updated[1]["spec"]["services"]["worker"]
    assert worker_patch["component_type"] == "worker"
    assert worker_patch["resource_shape"] == "gpu.a10"
    assert worker_patch["min_replicas"] == 1
    assert worker_patch["affinity"] == {"allowed_dedicated_node_groups": ["ng-1"]}
    assert worker_patch["extra_pod_spec"]["main_container"]["image"] == VLLM_IMAGE


def test_update_frontend_node_group_syncs_workers(fake, monkeypatch):
    class TwoGroups(FakeNodeGroupAPI):
        def list_all(self):
            return super().list_all() + [
                DedicatedNodeGroup(
                    metadata=Metadata(id="ng-2", name="other-ng"),
                    spec=DedicatedNodeGroupSpec(),
                    status=DedicatedNodeGroupStatus(),
                )
            ]

    monkeypatch.setattr(
        FakeAPIClient,
        "__init__",
        lambda self, *a, **k: (
            setattr(self, "dynamo", fake),
            setattr(self, "nodegroup", TwoGroups()),
            setattr(self, "shapes", FakeShapesAPI()),
        )
        and None,
    )
    result = run(
        "update",
        "-n",
        "my-dynamo",
        "-svc",
        "frontend",
        "--node-group",
        "other-ng",
        "-y",
    )
    assert result.exit_code == 0, result.output
    services = fake.updated[1]["spec"]["services"]
    assert services["frontend"]["affinity"] == {
        "allowed_dedicated_node_groups": ["ng-2"]
    }
    assert services["worker"]["affinity"] == {"allowed_dedicated_node_groups": ["ng-2"]}


# ---------------------------------------------------------------------------
# lep log get --dynamo
# ---------------------------------------------------------------------------


def test_log_get_dynamo_flag_validation():
    runner = CliRunner()
    result = runner.invoke(cli, ["log", "get", "--dynamo-service", "frontend"])
    assert result.exit_code == 1
    assert "requires --dynamo" in result.output or "No deployment name" in result.output

    result = runner.invoke(cli, ["log", "get", "--dynamo", "x", "-e", "y"])
    assert result.exit_code == 1
    assert "Only one of" in result.output


def test_group_help_lists_commands():
    result = CliRunner().invoke(cli, ["dynamo", "--help"])
    assert result.exit_code == 0
    for command in (
        "create",
        "get",
        "history",
        "metrics",
        "remove",
        "replica",
        "service",
        "status",
        "update",
        "list",
    ):
        assert command in result.output

    result = CliRunner().invoke(cli, ["dynamo", "service", "--help"])
    assert result.exit_code == 0
    for command in ("get", "list", "restart"):
        assert command in result.output

    result = CliRunner().invoke(cli, ["dynamo", "replica", "--help"])
    assert result.exit_code == 0
    for command in ("list", "log", "metrics", "remove"):
        assert command in result.output
