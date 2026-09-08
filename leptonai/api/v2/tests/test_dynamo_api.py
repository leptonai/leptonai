"""HTTP contract tests for DynamoGraphDeploymentAPI and the Dynamo LogAPI scope."""

import json
import os
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

import responses

from leptonai.api.v2.api_resource import ClientError
from leptonai.api.v2.client import APIClient
from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.dynamo import (
    LeptonDynamoGraphDeployment,
    LeptonDynamoGraphDeploymentState,
    LeptonDynamoGraphDeploymentUserSpec,
    LeptonDynamoServiceSpec,
)
from leptonai.api.v2.types.readiness import ReplicaReadinessReason

BASE = "https://gw.example/api/v2/workspaces/ws1"
DGD = f"{BASE}/dynamographdeployments"


def _client():
    return APIClient(workspace_id="ws1", auth_token="tok", url=BASE)


def _deployment_body(name="dyn-1", state="Ready"):
    return {
        "metadata": {"id": name, "name": name, "created_at": 1717000000000},
        "spec": {
            "dynamo_version": "1.3.1",
            "backend_framework": "vllm",
            "ingress_enabled": True,
            "services": {
                "frontend": {
                    "component_type": "frontend",
                    "resource_shape": "cpu.small",
                    "min_replicas": 1,
                    "max_replicas": 1,
                    "affinity": {"allowed_dedicated_node_groups": ["ng-1"]},
                    "mounts": [
                        {"path": "/d", "mount_path": "/mnt/d", "from": "node-nfs:x"}
                    ],
                    "extra_pod_spec": {
                        "main_container": {
                            "image": "nvcr.io/nvidia/ai-dynamo/vllm-runtime:1.3.1",
                            "command": ["/bin/sh", "-c", "python3 -m dynamo.frontend"],
                        }
                    },
                }
            },
        },
        "status": {
            "state": state,
            "services": {
                "frontend": {
                    "state": "Ready",
                    "ready_replicas": 1,
                    "desired_replicas": 1,
                }
            },
            "endpoint": {"external_endpoint": "https://dyn-1.example.com"},
        },
    }


def _replica_body(rid="frontend-abc", reason="Ready"):
    return {
        "metadata": {"id": rid, "name": rid, "created_at": 1717000000000},
        "id": rid,
        "status": {
            "readiness_issue": {
                "reason": reason,
                "message": "",
                "creationTimestamp": "2024-01-01T00:00:00Z",
            },
            "node": {"name": "node-1", "id": "n-1", "node_group_id": "ng-1"},
        },
    }


def _last_request():
    return responses.calls[-1].request


def _query(request):
    return parse_qs(urlparse(request.url).query)


class TestDynamoGraphDeploymentAPI(unittest.TestCase):
    @responses.activate
    def test_list_all_parses_bare_array_and_states(self):
        responses.add(
            responses.GET,
            DGD,
            json=[_deployment_body("a", "Ready"), _deployment_body("b", "Not Ready")],
        )
        items = _client().dynamo.list_all()
        self.assertEqual([d.metadata.name for d in items], ["a", "b"])
        self.assertEqual(items[0].status.state, LeptonDynamoGraphDeploymentState.Ready)
        self.assertEqual(
            items[1].status.state, LeptonDynamoGraphDeploymentState.NotReady
        )
        self.assertEqual(
            items[0].spec.services["frontend"].mounts[0].from_, "node-nfs:x"
        )
        self.assertEqual(
            items[0].status.endpoint.external_endpoint, "https://dyn-1.example.com"
        )

    @responses.activate
    def test_unknown_state_maps_to_unknown(self):
        responses.add(responses.GET, DGD, json=[_deployment_body("a", "Weird")])
        items = _client().dynamo.list_all()
        self.assertEqual(
            items[0].status.state, LeptonDynamoGraphDeploymentState.Unknown
        )

    @responses.activate
    def test_get_and_not_found(self):
        responses.add(responses.GET, f"{DGD}/dyn-1", json=_deployment_body())
        responses.add(
            responses.GET,
            f"{DGD}/missing",
            json={"code": "ResourceNotFound", "message": "not found"},
            status=404,
        )
        client = _client()
        dep = client.dynamo.get("dyn-1")
        self.assertEqual(dep.metadata.id_, "dyn-1")
        # Objects are accepted anywhere a name is.
        client.dynamo.get(dep)
        self.assertTrue(_last_request().url.endswith("/dynamographdeployments/dyn-1"))
        with self.assertRaises(ClientError):
            client.dynamo.get("missing")

    @responses.activate
    def test_create_sends_aliased_payload_without_nones(self):
        responses.add(responses.POST, DGD, json=_deployment_body(), status=201)
        spec = LeptonDynamoGraphDeploymentUserSpec(
            backend_framework="vllm",
            ingress_enabled=True,
            services={
                "frontend": LeptonDynamoServiceSpec(
                    component_type="frontend",
                    resource_shape="cpu.small",
                    min_replicas=1,
                    mounts=[
                        {"path": "/d", "mount_path": "/mnt/d", "from": "node-nfs:x"}
                    ],
                )
            },
        )
        dep = LeptonDynamoGraphDeployment(metadata=Metadata(name="dyn-1"), spec=spec)
        created = _client().dynamo.create(dep)
        self.assertEqual(created.metadata.name, "dyn-1")

        body = json.loads(_last_request().body)
        self.assertEqual(body["metadata"], {"name": "dyn-1"})
        self.assertNotIn("dynamo_namespace", body["spec"])
        frontend = body["spec"]["services"]["frontend"]
        self.assertEqual(frontend["min_replicas"], 1)
        self.assertNotIn("max_replicas", frontend)
        self.assertEqual(frontend["mounts"][0]["from"], "node-nfs:x")

    @responses.activate
    def test_update_sends_merge_patch_and_dryrun(self):
        responses.add(responses.PATCH, f"{DGD}/dyn-1", json=_deployment_body())
        client = _client()
        patch = {
            "spec": {"services": {"worker": None, "frontend": {"min_replicas": 2}}}
        }

        client.dynamo.update("dyn-1", patch)
        request = _last_request()
        self.assertEqual(json.loads(request.body), patch)
        self.assertEqual(_query(request), {})

        client.dynamo.update("dyn-1", patch, dryrun=True)
        self.assertEqual(_query(_last_request()), {"dryrun": ["true"]})

        with self.assertRaises(ValueError):
            client.dynamo.update("dyn-1", ["not", "a", "dict"])  # type: ignore[arg-type]

    @responses.activate
    def test_delete(self):
        responses.add(responses.DELETE, f"{DGD}/dyn-1", json=_deployment_body())
        self.assertTrue(_client().dynamo.delete("dyn-1"))

    @responses.activate
    def test_services_and_service(self):
        responses.add(
            responses.GET,
            f"{DGD}/dyn-1/services",
            json={
                "services": {
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
            },
        )
        responses.add(
            responses.GET,
            f"{DGD}/dyn-1/services/worker",
            json={
                "name": "worker",
                "component_type": "worker",
                "resource_shape": "gpu.h100-8",
                "min_replicas": 2,
                "ready_replicas": 1,
                "spec": {"component_type": "worker", "min_replicas": 2},
                "status": {
                    "state": "Starting",
                    "phase": "Running",
                    "health": "degraded",
                    "replicas": {
                        "desired": 2,
                        "ready": 1,
                        "running": 2,
                        "total_pods": 4,
                    },
                    "conditions": [{
                        "type": "Available",
                        "status": "False",
                        "reason": "Pending",
                        "message": "m",
                    }],
                    "uptime": 42,
                },
            },
        )
        client = _client()
        services = client.dynamo.list_services("dyn-1").services
        self.assertEqual(sorted(services), ["frontend", "worker"])
        self.assertTrue(services["worker"].is_multinode)
        self.assertEqual(services["worker"].node_count, 2)

        service = client.dynamo.get_service("dyn-1", "worker")
        self.assertEqual(service.status.replicas.ready, 1)
        self.assertEqual(service.status.conditions[0].type_, "Available")
        self.assertEqual(service.status.uptime, 42)

    @responses.activate
    def test_restart_service_uses_put(self):
        responses.add(
            responses.PUT,
            f"{DGD}/dyn-1/services/worker/restart",
            json={
                "message": "restarted",
                "service": "worker",
                "deleted_pods": ["p1", "p2"],
            },
        )
        resp = _client().dynamo.restart_service("dyn-1", "worker")
        self.assertEqual(resp.deleted_pods, ["p1", "p2"])
        self.assertEqual(_last_request().method, "PUT")

    @responses.activate
    def test_replica_listing(self):
        responses.add(
            responses.GET,
            f"{DGD}/dyn-1/replicas",
            json=[_replica_body("frontend-abc"), _replica_body("worker-xyz", "Failed")],
        )
        responses.add(
            responses.GET,
            f"{DGD}/dyn-1/services/worker/replicas",
            json={
                "service": "worker",
                "replicas": [_replica_body("worker-xyz", "WaitingForCapacity")],
                "is_multinode": True,
                "node_count": 2,
            },
        )
        client = _client()

        flat = client.dynamo.list_replicas("dyn-1")
        self.assertEqual([r.metadata.id_ for r in flat], ["frontend-abc", "worker-xyz"])
        self.assertEqual(
            flat[0].status.readiness_issue.reason, ReplicaReadinessReason.Ready
        )
        self.assertEqual(
            flat[1].status.readiness_issue.reason, ReplicaReadinessReason.Failed
        )
        self.assertEqual(flat[0].status.node.node_group_id, "ng-1")
        self.assertEqual(_query(_last_request()), {})

        client.dynamo.list_replicas("dyn-1", service="worker")
        self.assertEqual(_query(_last_request()), {"service": ["worker"]})

        scoped = client.dynamo.list_service_replicas("dyn-1", "worker")
        self.assertEqual(scoped.service, "worker")
        self.assertTrue(scoped.is_multinode)
        self.assertEqual(
            scoped.replicas[0].status.readiness_issue.reason,
            ReplicaReadinessReason.WaitingForCapacity,
        )

    @responses.activate
    def test_replica_log_paths_and_query(self):
        payload = {
            "deployment": "dyn-1",
            "service": "worker",
            "replica": "w-1",
            "logs": "a\nb\n",
        }
        responses.add(responses.GET, f"{DGD}/dyn-1/replicas/w-1/log", json=payload)
        responses.add(
            responses.GET, f"{DGD}/dyn-1/services/worker/replicas/w-1/log", json=payload
        )
        client = _client()

        resp = client.dynamo.get_replica_log("dyn-1", "w-1")
        self.assertEqual(resp.logs, "a\nb\n")
        self.assertTrue(_last_request().url.endswith("/replicas/w-1/log"))
        self.assertEqual(_query(_last_request()), {})

        client.dynamo.get_replica_log(
            "dyn-1", "w-1", service="worker", tail=50, timestamps=True
        )
        request = _last_request()
        self.assertIn("/services/worker/replicas/w-1/log", request.url)
        self.assertEqual(_query(request), {"tail": ["50"], "timestamps": ["true"]})

        with self.assertRaises(ValueError):
            client.dynamo.get_replica_log("dyn-1", "w-1", tail=0)

    @responses.activate
    def test_delete_replica_paths(self):
        payload = {"message": "deleted", "replica": "w-1", "service": "worker"}
        responses.add(responses.DELETE, f"{DGD}/dyn-1/replicas/w-1", json=payload)
        responses.add(
            responses.DELETE, f"{DGD}/dyn-1/services/worker/replicas/w-1", json=payload
        )
        client = _client()
        self.assertEqual(client.dynamo.delete_replica("dyn-1", "w-1").replica, "w-1")
        self.assertTrue(_last_request().url.endswith("/replicas/w-1"))
        client.dynamo.delete_replica("dyn-1", "w-1", service="worker")
        self.assertIn("/services/worker/replicas/w-1", _last_request().url)

    @responses.activate
    def test_monitoring_status_history_and_metrics(self):
        responses.add(
            responses.GET,
            f"{DGD}/dyn-1/monitoring/status",
            json={
                "overall_health": "degraded",
                "total_services": 2,
                "healthy_services": 1,
                "services": {"frontend": "healthy", "worker": "unhealthy"},
            },
        )
        responses.add(
            responses.GET,
            f"{DGD}/dyn-1/history",
            json=[
                {"timestamp": 1717000000000, "operation": "create", "description": "d"}
            ],
        )
        series = [
            {"metric": {"name": "GPUUtilAvg", "device": "0"}, "values": [[1, "0.5"]]}
        ]
        responses.add(responses.GET, f"{DGD}/dyn-1/monitoring/GPUUtilAvg", json=series)
        responses.add(
            responses.GET, f"{DGD}/dyn-1/replicas/w-1/monitoring/GPUUtil", json=series
        )
        client = _client()

        health = client.dynamo.get_monitoring_status("dyn-1")
        self.assertEqual(health.overall_health, "degraded")
        self.assertEqual(health.services["worker"], "unhealthy")

        history = client.dynamo.get_history("dyn-1")
        self.assertEqual(history[0].operation, "create")

        self.assertEqual(
            client.dynamo.get_metric("dyn-1", "GPUUtilAvg", window=6), series
        )
        self.assertEqual(_query(_last_request()), {"window": ["6"]})

        self.assertEqual(
            client.dynamo.get_replica_metric("dyn-1", "w-1", "GPUUtil"), series
        )
        self.assertEqual(_query(_last_request()), {})


class TestLogAPIDynamoScope(unittest.TestCase):
    @responses.activate
    def test_get_log_sends_dynamo_query_keys(self):
        responses.add(responses.GET, f"{BASE}/logs", json={"data": {"result": []}})
        _client().log.get_log(
            name_or_dynamo="dyn-1",
            dynamo_service="frontend",
            replica="r-1",
            start=1,
            end=2,
        )
        query = _query(_last_request())
        self.assertEqual(query["dynamo_graph_deployment"], ["dyn-1"])
        self.assertEqual(query["dynamo_service"], ["frontend"])
        self.assertEqual(query["replica"], ["r-1"])
        self.assertNotIn("deployment", query)
        self.assertNotIn("endpoint", query)

    @responses.activate
    def test_time_series_accepts_dynamo_object(self):
        responses.add(responses.GET, f"{BASE}/logs/timeseries", json={})
        dep = LeptonDynamoGraphDeployment(metadata=Metadata(id="dyn-9", name="dyn-9"))
        _client().log.get_log_time_series(name_or_dynamo=dep, start=1, end=2)
        self.assertEqual(_query(_last_request())["dynamo_graph_deployment"], ["dyn-9"])


if __name__ == "__main__":
    unittest.main()
