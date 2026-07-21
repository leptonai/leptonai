"""Tests for the new /endpoints + /devpods API dispatch (LEP-5664 / LEP-5665).

These use ``responses`` to mock the HTTP layer. The SDK talks to the backend
through ``requests.Session`` (see APIClient), so ``responses`` — not ``respx``
(which mocks httpx) — is the correct mocking library here.

Coverage:
- flag detection: features.enable_new_deployment_api explicit-true semantics,
  fail-safe to legacy on absent / false / missing-features / info() error
- flag caching: a single /workspace call resolves the flag for the client
- flag OFF: deployment/pod command paths hit the legacy /deployments routes
  byte-identically
- flag ON: endpoint command paths hit /endpoints; devpod paths hit /devpods
- pod create path: legacy POST /deployments (off) vs POST /devpods (on)
"""

import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai, matching
# the existing CLI test suite so tests never touch a real workspace record.
os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

import unittest

import responses

from leptonai.api.v2.client import APIClient
from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.deployment import (
    LeptonDeployment,
    LeptonDeploymentUserSpec,
    LeptonContainer,
    ResourceRequirement,
)

BASE = "https://gw.example/api/v2/workspaces/ws1"


def _make_client() -> APIClient:
    return APIClient(workspace_id="ws1", auth_token="tok", url=BASE)


def _workspace_info(enable_new_deployment_api=None, include_features=True):
    """A minimal but schema-valid /workspace info body."""
    info = {
        "build_time": "t",
        "git_commit": "0.1.2",
        "workspace_name": "ws1",
        "workspace_tier": "basic",
        "workspace_state": "normal",
        "supported_shapes": {},
        "workspace_disk_usage_bytes": 0,
        "workloads": {
            "num_deployments": 0,
            "num_jobs": 0,
            "num_pods": 0,
            "num_secrets": 0,
            "num_image_pull_secrets": 0,
        },
        "resource_quota": {
            "limit": {"cpu": 0.0, "memory": 0, "accelerator_num": 0.0},
            "used": {"cpu": 0.0, "memory": 0, "accelerator_num": 0.0},
        },
    }
    if include_features:
        features = {}
        if enable_new_deployment_api is not None:
            features["enable_new_deployment_api"] = enable_new_deployment_api
        info["features"] = features
    return info


def _register_workspace(enable_new_deployment_api=None, include_features=True):
    responses.add(
        responses.GET,
        f"{BASE}/workspace",
        json=_workspace_info(enable_new_deployment_api, include_features),
        status=200,
    )


def _endpoint_body(name="my-ep"):
    return {
        "metadata": {"id": name, "name": name, "created_at": 1},
        "spec": {
            "components": [{
                "name": "default",
                "image": "nginx",
                "resource_shape": "cpu.small",
                "min_replicas": 1,
            }]
        },
        "status": {"state": "Ready", "external_url": "https://x.example"},
    }


def _devpod_body(name="my-pod", stopped=False):
    return {
        "metadata": {"name": name, "created_at": 1},
        "spec": {
            "container": {"image": "ubuntu"},
            "resource_shape": "cpu.small",
            "stopped": stopped,
        },
        "status": {"state": "Ready"},
    }


def _pod_spec(name="my-pod"):
    return LeptonDeployment(
        metadata=Metadata(name=name),
        spec=LeptonDeploymentUserSpec(
            container=LeptonContainer(image="ubuntu"),
            resource_requirement=ResourceRequirement(resource_shape="cpu.small"),
            is_pod=True,
        ),
    )


def _deployment_spec(name="my-ep"):
    return LeptonDeployment(
        metadata=Metadata(name=name),
        spec=LeptonDeploymentUserSpec(
            container=LeptonContainer(image="nginx"),
            resource_requirement=ResourceRequirement(
                resource_shape="cpu.small", min_replicas=1
            ),
        ),
    )


def _urls_called():
    return [c.request.url for c in responses.calls]


class TestFlagDetection(unittest.TestCase):
    @responses.activate
    def test_explicit_true_enables_new_api(self):
        _register_workspace(enable_new_deployment_api=True)
        client = _make_client()
        self.assertTrue(client.new_deployment_api_enabled)

    @responses.activate
    def test_explicit_false_stays_legacy(self):
        _register_workspace(enable_new_deployment_api=False)
        client = _make_client()
        self.assertFalse(client.new_deployment_api_enabled)

    @responses.activate
    def test_absent_flag_stays_legacy(self):
        # features present but flag key absent -> legacy
        _register_workspace(enable_new_deployment_api=None)
        client = _make_client()
        self.assertFalse(client.new_deployment_api_enabled)

    @responses.activate
    def test_missing_features_object_stays_legacy(self):
        _register_workspace(include_features=False)
        client = _make_client()
        self.assertFalse(client.new_deployment_api_enabled)

    @responses.activate
    def test_info_error_fails_safe_to_legacy(self):
        responses.add(responses.GET, f"{BASE}/workspace", status=500)
        client = _make_client()
        self.assertFalse(client.new_deployment_api_enabled)

    @responses.activate
    def test_flag_is_cached_single_workspace_call(self):
        _register_workspace(enable_new_deployment_api=True)
        client = _make_client()
        # Access several times; only one /workspace call should be made.
        for _ in range(5):
            self.assertTrue(client.new_deployment_api_enabled)
        workspace_calls = [
            c for c in responses.calls if c.request.url == f"{BASE}/workspace"
        ]
        self.assertEqual(len(workspace_calls), 1)


class TestFlagOffLegacyRoutes(unittest.TestCase):
    @responses.activate
    def test_list_uses_legacy_deployments(self):
        _register_workspace(enable_new_deployment_api=False)
        responses.add(responses.GET, f"{BASE}/deployments", json=[], status=200)
        client = _make_client()
        client.deployment.list_all()
        self.assertIn(f"{BASE}/deployments", _urls_called())

    @responses.activate
    def test_create_uses_legacy_deployments(self):
        _register_workspace(enable_new_deployment_api=False)
        responses.add(responses.POST, f"{BASE}/deployments", json={}, status=200)
        client = _make_client()
        client.deployment.create(_deployment_spec())
        posts = [c.request.url for c in responses.calls if c.request.method == "POST"]
        self.assertEqual(posts, [f"{BASE}/deployments"])

    @responses.activate
    def test_pod_create_uses_legacy_deployments(self):
        _register_workspace(enable_new_deployment_api=False)
        responses.add(responses.POST, f"{BASE}/deployments", json={}, status=200)
        client = _make_client()
        client.pod.create(_pod_spec())
        posts = [c.request.url for c in responses.calls if c.request.method == "POST"]
        self.assertEqual(posts, [f"{BASE}/deployments"])


class TestFlagOnEndpointRoutes(unittest.TestCase):
    @responses.activate
    def test_list_uses_endpoints(self):
        _register_workspace(enable_new_deployment_api=True)
        responses.add(
            responses.GET, f"{BASE}/endpoints", json=[_endpoint_body()], status=200
        )
        client = _make_client()
        result = client.deployment.list_all()
        self.assertIn(f"{BASE}/endpoints", _urls_called())
        self.assertNotIn(f"{BASE}/deployments", _urls_called())
        self.assertEqual(result[0].metadata.name, "my-ep")
        self.assertEqual(result[0].spec.container.image, "nginx")

    @responses.activate
    def test_get_uses_endpoints_and_translates(self):
        _register_workspace(enable_new_deployment_api=True)
        responses.add(
            responses.GET, f"{BASE}/endpoints/my-ep", json=_endpoint_body(), status=200
        )
        client = _make_client()
        dep = client.deployment.get("my-ep")
        self.assertIn(f"{BASE}/endpoints/my-ep", _urls_called())
        self.assertEqual(dep.spec.resource_requirement.resource_shape, "cpu.small")
        self.assertEqual(dep.status.endpoint.external_endpoint, "https://x.example")

    @responses.activate
    def test_create_posts_component_payload_to_endpoints(self):
        _register_workspace(enable_new_deployment_api=True)
        responses.add(responses.POST, f"{BASE}/endpoints", json={}, status=200)
        client = _make_client()
        client.deployment.create(_deployment_spec())
        post_calls = [c for c in responses.calls if c.request.method == "POST"]
        self.assertEqual(len(post_calls), 1)
        self.assertEqual(post_calls[0].request.url, f"{BASE}/endpoints")
        import json as _json

        body = _json.loads(post_calls[0].request.body)
        # legacy container/resource_requirement collapse into a component
        self.assertIn("components", body["spec"])
        self.assertEqual(body["spec"]["components"][0]["image"], "nginx")

    @responses.activate
    def test_update_fetches_then_patches_full_components(self):
        _register_workspace(enable_new_deployment_api=True)
        responses.add(
            responses.GET, f"{BASE}/endpoints/my-ep", json=_endpoint_body(), status=200
        )
        responses.add(
            responses.PATCH,
            f"{BASE}/endpoints/my-ep",
            json=_endpoint_body(),
            status=200,
        )
        client = _make_client()
        spec = _deployment_spec()
        spec.spec.container.image = "nginx:2"
        client.deployment.update("my-ep", spec)
        methods = [(c.request.method, c.request.url) for c in responses.calls]
        # a GET (fetch live) precedes the PATCH (full component array)
        self.assertIn(("GET", f"{BASE}/endpoints/my-ep"), methods)
        self.assertIn(("PATCH", f"{BASE}/endpoints/my-ep"), methods)

    @responses.activate
    def test_restart_puts_to_endpoints(self):
        _register_workspace(enable_new_deployment_api=True)
        responses.add(
            responses.PUT,
            f"{BASE}/endpoints/my-ep/restart",
            json=_endpoint_body(),
            status=200,
        )
        client = _make_client()
        client.deployment.restart("my-ep")
        self.assertIn(f"{BASE}/endpoints/my-ep/restart", _urls_called())

    @responses.activate
    def test_replicas_and_events_use_endpoint_subroutes(self):
        _register_workspace(enable_new_deployment_api=True)
        responses.add(
            responses.GET, f"{BASE}/endpoints/my-ep/replicas", json=[], status=200
        )
        responses.add(
            responses.GET, f"{BASE}/endpoints/my-ep/events", json=[], status=200
        )
        client = _make_client()
        client.deployment.get_replicas("my-ep")
        client.deployment.get_events("my-ep")
        urls = _urls_called()
        self.assertIn(f"{BASE}/endpoints/my-ep/replicas", urls)
        self.assertIn(f"{BASE}/endpoints/my-ep/events", urls)

    @responses.activate
    def test_readiness_and_termination_degrade(self):
        from leptonai.api.v2.endpoint import NewEndpointAPIUnsupported

        _register_workspace(enable_new_deployment_api=True)
        client = _make_client()
        with self.assertRaises(NewEndpointAPIUnsupported):
            client.deployment.get_readiness("my-ep")
        with self.assertRaises(NewEndpointAPIUnsupported):
            client.deployment.get_termination("my-ep")


class TestFlagOnDevPodRoutes(unittest.TestCase):
    @responses.activate
    def test_list_uses_devpods(self):
        _register_workspace(enable_new_deployment_api=True)
        responses.add(
            responses.GET, f"{BASE}/devpods", json=[_devpod_body()], status=200
        )
        client = _make_client()
        result = client.pod.list_all()
        self.assertIn(f"{BASE}/devpods", _urls_called())
        self.assertTrue(result[0].spec.is_pod)

    @responses.activate
    def test_pod_create_posts_to_devpods(self):
        _register_workspace(enable_new_deployment_api=True)
        responses.add(responses.POST, f"{BASE}/devpods", json={}, status=200)
        client = _make_client()
        client.pod.create(_pod_spec())
        post_calls = [c for c in responses.calls if c.request.method == "POST"]
        self.assertEqual(len(post_calls), 1)
        self.assertEqual(post_calls[0].request.url, f"{BASE}/devpods")
        import json as _json

        body = _json.loads(post_calls[0].request.body)
        # resource_shape lifted to spec level; no resource_requirement / is_pod
        self.assertEqual(body["spec"]["resource_shape"], "cpu.small")
        self.assertNotIn("resource_requirement", body["spec"])
        self.assertNotIn("is_pod", body["spec"])

    @responses.activate
    def test_get_uses_devpods_and_translates(self):
        _register_workspace(enable_new_deployment_api=True)
        responses.add(
            responses.GET, f"{BASE}/devpods/my-pod", json=_devpod_body(), status=200
        )
        client = _make_client()
        pod = client.pod.get("my-pod")
        self.assertIn(f"{BASE}/devpods/my-pod", _urls_called())
        self.assertTrue(pod.spec.is_pod)
        self.assertEqual(pod.spec.resource_requirement.resource_shape, "cpu.small")

    @responses.activate
    def test_stop_uses_stopped_switch(self):
        _register_workspace(enable_new_deployment_api=True)
        responses.add(
            responses.PATCH,
            f"{BASE}/devpods/my-pod",
            json=_devpod_body(stopped=True),
            status=200,
        )
        client = _make_client()
        client.pod.stop("my-pod")
        patch_calls = [c for c in responses.calls if c.request.method == "PATCH"]
        self.assertEqual(len(patch_calls), 1)
        self.assertEqual(patch_calls[0].request.url, f"{BASE}/devpods/my-pod")
        import json as _json

        body = _json.loads(patch_calls[0].request.body)
        self.assertEqual(body, {"spec": {"stopped": True}})

    @responses.activate
    def test_delete_uses_devpods(self):
        _register_workspace(enable_new_deployment_api=True)
        responses.add(responses.DELETE, f"{BASE}/devpods/my-pod", json={}, status=200)
        client = _make_client()
        client.pod.delete("my-pod")
        self.assertIn(f"{BASE}/devpods/my-pod", _urls_called())

    @responses.activate
    def test_restart_puts_to_devpods(self):
        _register_workspace(enable_new_deployment_api=True)
        responses.add(
            responses.PUT,
            f"{BASE}/devpods/my-pod/restart",
            json=_devpod_body(),
            status=200,
        )
        client = _make_client()
        client.pod.restart("my-pod")
        self.assertIn(f"{BASE}/devpods/my-pod/restart", _urls_called())

    @responses.activate
    def test_log_degrades(self):
        from leptonai.api.v2.devpod import NewDevPodAPIUnsupported

        _register_workspace(enable_new_deployment_api=True)
        client = _make_client()
        with self.assertRaises(NewDevPodAPIUnsupported):
            client.pod.get_log("my-pod")


class TestGate403SurfacesCleanly(unittest.TestCase):
    @responses.activate
    def test_devpod_gate_403_raises_client_error_with_message(self):
        from leptonai.api.v2.api_resource import ClientError

        _register_workspace(enable_new_deployment_api=True)
        responses.add(
            responses.GET,
            f"{BASE}/devpods",
            json={
                "code": "StatusForbidden",
                "message": "the new devpod API is not enabled for this workspace",
            },
            status=403,
        )
        client = _make_client()
        with self.assertRaises(ClientError) as ctx:
            client.pod.list_all()
        # The gate message is carried in the error for the CLI to render.
        self.assertIn("not enabled for this workspace", str(ctx.exception))
        self.assertEqual(ctx.exception.response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
