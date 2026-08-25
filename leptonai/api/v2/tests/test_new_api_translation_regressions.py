"""Regression tests for compatibility gaps found during the max-effort review."""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from types import SimpleNamespace
from unittest.mock import Mock

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

from requests import Response

from leptonai.api.v2 import translation
from leptonai.api.v2.devpod import DevPodAPI, NewDevPodAPIUnsupported
from leptonai.api.v2.endpoint import EndpointAPI, NewEndpointAPIUnsupported
from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.deployment import (
    LeptonContainer,
    LeptonDeployment,
    LeptonDeploymentUserSpec,
    ResourceRequirement,
    TokenVar,
)


def _response(payload, status=200):
    response = Response()
    response.status_code = status
    response._content = json.dumps(payload).encode()
    response.headers["Content-Type"] = "application/json"
    return response


def _resource_client(get_response=None):
    return SimpleNamespace(
        _get=lambda *args, **kwargs: get_response,
        _post=lambda *args, **kwargs: None,
        _put=lambda *args, **kwargs: None,
        _patch=lambda *args, **kwargs: None,
        _delete=lambda *args, **kwargs: None,
        _head=lambda *args, **kwargs: None,
    )


class TestEndpointTranslationRegressions(unittest.TestCase):
    def test_disabled_ingress_survives_get_export_and_create(self):
        raw = {
            "metadata": {"name": "private-endpoint"},
            "spec": {
                "ingress_enabled": False,
                "components": [{"name": "default", "image": "nginx"}],
            },
            "status": {"state": "Ready"},
        }
        posts = []
        fake = _resource_client(_response(raw))
        fake._post = lambda path, **kwargs: (
            posts.append((path, kwargs["json"])) or _response({})
        )
        api = EndpointAPI(fake)

        model = api.get("private-endpoint")
        self.assertIs(model.spec.ingress_enabled, False)

        # This is the exact spec-only representation written by `lep endpoint
        # get --path`. Loading it into a fresh model must retain explicit false.
        exported = json.loads(model.spec.model_dump_json(by_alias=True))
        self.assertIs(exported["ingress_enabled"], False)
        recreated = LeptonDeployment(
            metadata=Metadata(name="private-endpoint-copy"),
            spec=LeptonDeploymentUserSpec(**exported),
        )

        self.assertTrue(api.create(recreated))
        self.assertEqual(posts[0][0], "/endpoints")
        self.assertIs(posts[0][1]["spec"]["ingress_enabled"], False)

    def test_create_without_ports_injects_legacy_default(self):
        wire = translation.legacy_to_http_endpoint({
            "metadata": {"name": "ep"},
            "spec": {
                "container": {"image": "nginx"},
                "resource_requirement": {"resource_shape": "cpu.small"},
            },
        })
        self.assertEqual(
            wire["spec"]["components"][0]["ports"],
            [{"container_port": 40000}],
        )

    def test_destructive_endpoint_patches_reject_ambiguous_snapshots(self):
        invalid_snapshots = {
            "missing spec": {},
            "null spec": {"spec": None},
            "missing components": {"spec": {}},
            "null components": {"spec": {"components": None}},
            "empty components": {"spec": {"components": []}},
            "non-list components": {"spec": {"components": {}}},
            "non-dict component": {"spec": {"components": [None]}},
            "missing component name": {"spec": {"components": [{"image": "nginx"}]}},
            "duplicate component names": {
                "spec": {
                    "components": [
                        {"name": "duplicate", "frontend": True},
                        {"name": "duplicate"},
                    ]
                }
            },
            "multi-component without frontend": {
                "spec": {"components": [{"name": "api"}, {"name": "worker"}]}
            },
            "multi-component with two frontends": {
                "spec": {
                    "components": [
                        {"name": "api", "frontend": True},
                        {"name": "worker", "frontend": True},
                    ]
                }
            },
        }
        legacy_update = {
            "metadata": {},
            "spec": {"container": {"image": "nginx:updated"}},
        }
        builders = {
            "update": lambda raw: translation.legacy_to_http_endpoint_patch(
                raw, legacy_update
            ),
            "stop": translation.build_endpoint_stop_patch,
        }

        for snapshot_name, raw in invalid_snapshots.items():
            for builder_name, builder in builders.items():
                with self.subTest(snapshot=snapshot_name, builder=builder_name):
                    with self.assertRaises(ValueError):
                        builder(raw)

    def test_destructive_endpoint_patches_accept_valid_snapshots(self):
        legacy_update = {
            "metadata": {},
            "spec": {"container": {"image": "nginx:updated"}},
        }
        valid_snapshots = {
            "single": {
                "spec": {"components": [{"name": "only", "image": "nginx:old"}]}
            },
            "multi": {
                "spec": {
                    "components": [
                        {"name": "worker", "image": "worker:old"},
                        {"name": "api", "image": "api:old", "frontend": True},
                    ]
                }
            },
        }

        for snapshot_name, raw in valid_snapshots.items():
            with self.subTest(snapshot=snapshot_name):
                update = translation.legacy_to_http_endpoint_patch(raw, legacy_update)
                update_components = update["spec"]["components"]
                self.assertEqual(
                    [component["name"] for component in update_components],
                    [component["name"] for component in raw["spec"]["components"]],
                )
                expected_frontend_index = 0 if snapshot_name == "single" else 1
                self.assertEqual(
                    update_components[expected_frontend_index]["image"],
                    "nginx:updated",
                )
                if snapshot_name == "multi":
                    self.assertEqual(update_components[0], raw["spec"]["components"][0])

                stop = translation.build_endpoint_stop_patch(raw)
                self.assertEqual(
                    [component["name"] for component in stop["spec"]["components"]],
                    [component["name"] for component in raw["spec"]["components"]],
                )
                self.assertTrue(
                    all(
                        component["min_replicas"] == 0
                        for component in stop["spec"]["components"]
                    )
                )

    def test_stop_disables_active_gpu_and_qpm_targets(self):
        raw = {
            "spec": {
                "components": [
                    {
                        "name": "gpu",
                        "frontend": True,
                        "min_replicas": 1,
                        "autoscaling": {
                            "target_gpu_utilization_percentage": 50,
                            "scale_down": {"no_traffic_timeout": 600},
                        },
                    },
                    {
                        "name": "qpm",
                        "min_replicas": 1,
                        "autoscaling": {
                            "target_throughput": {
                                "qpm": 10,
                                "paths": ["/predict"],
                                "methods": ["POST"],
                            }
                        },
                    },
                    {
                        "name": "scale-down-only",
                        "min_replicas": 1,
                        "autoscaling": {"scale_down": {"no_traffic_timeout": 300}},
                    },
                ]
            }
        }

        patch = translation.build_endpoint_stop_patch(raw)
        gpu, qpm, scale_down_only = patch["spec"]["components"]
        self.assertEqual(gpu["min_replicas"], 0)
        self.assertEqual(gpu["autoscaling"]["target_gpu_utilization_percentage"], 0)
        self.assertEqual(gpu["autoscaling"]["scale_down"]["no_traffic_timeout"], 0)
        self.assertEqual(qpm["autoscaling"]["target_throughput"]["qpm"], 0)
        self.assertEqual(qpm["autoscaling"]["target_throughput"]["paths"], [])
        self.assertEqual(qpm["autoscaling"]["target_throughput"]["methods"], [])
        self.assertEqual(
            scale_down_only["autoscaling"]["scale_down"]["no_traffic_timeout"],
            300,
        )
        # Translation never mutates the server response supplied by the caller.
        self.assertEqual(
            raw["spec"]["components"][0]["autoscaling"][
                "target_gpu_utilization_percentage"
            ],
            50,
        )

    def test_metadata_id_and_owner_survive_create_and_update(self):
        legacy = {
            "metadata": {"id": "ep", "owner": "new-owner"},
            "spec": {"container": {"image": "nginx"}},
        }
        create = translation.legacy_to_http_endpoint(legacy)
        self.assertEqual(create["metadata"]["name"], "ep")
        self.assertEqual(create["metadata"]["lepton_metadata"]["owner"], "new-owner")

        raw = {"spec": {"components": [{"name": "default", "image": "nginx"}]}}
        update = translation.legacy_to_http_endpoint_patch(raw, legacy)
        self.assertEqual(update["metadata"]["lepton_metadata"]["owner"], "new-owner")

    def test_unsupported_legacy_port_exposure_is_rejected(self):
        legacy = {
            "metadata": {"name": "ep"},
            "spec": {
                "container": {
                    "image": "nginx",
                    "ports": [{"container_port": 8080, "host_port": 41000}],
                }
            },
        }
        with self.assertRaisesRegex(ValueError, "cannot represent"):
            translation.legacy_to_http_endpoint(legacy)

    def test_unsupported_direct_resource_fields_are_rejected(self):
        legacy = {
            "metadata": {"name": "ep"},
            "spec": {
                "container": {"image": "nginx"},
                "resource_requirement": {"cpu": 2.0, "memory": 4096},
            },
        }
        with self.assertRaisesRegex(ValueError, "resource_shape"):
            translation.legacy_to_http_endpoint(legacy)

    def test_endpoint_labels_are_rejected_instead_of_dropped(self):
        legacy = {
            "metadata": {"name": "ep", "labels": {"team": "inference"}},
            "spec": {"container": {"image": "nginx"}},
        }
        with self.assertRaisesRegex(ValueError, "metadata labels"):
            translation.legacy_to_http_endpoint(legacy)

    def test_endpoint_empty_labels_are_accepted_as_noop(self):
        wire = translation.legacy_to_http_endpoint({
            "metadata": {"name": "ep", "labels": {}},
            "spec": {"container": {"image": "nginx"}},
        })
        self.assertEqual(wire["metadata"]["name"], "ep")
        self.assertNotIn("labels", wire["metadata"])

    def test_storage_attachments_reach_endpoint_create(self):
        storage_attachments = [{
            "data_source_name": "my-bucket",
            "attachments": [{"mode": "awsProfile"}],
        }]
        wire = translation.legacy_to_http_endpoint({
            "metadata": {"name": "ep"},
            "spec": {
                "container": {"image": "nginx"},
                "storage_attachments": storage_attachments,
            },
        })
        self.assertEqual(
            wire["spec"]["components"][0]["storage_attachments"],
            storage_attachments,
        )

    def test_storage_attachments_reach_endpoint_update_patch(self):
        storage_attachments = [{
            "data_source_name": "my-bucket",
            "attachments": [{"mode": "mscProfile", "attach_with": "object"}],
        }]
        raw = {"spec": {"components": [{"name": "default", "image": "nginx"}]}}
        legacy = {
            "metadata": {"name": "ep"},
            "spec": {"storage_attachments": storage_attachments},
        }
        update = translation.legacy_to_http_endpoint_patch(raw, legacy)
        self.assertEqual(
            update["spec"]["components"][0]["storage_attachments"],
            storage_attachments,
        )

    def test_storage_attachments_round_trip_from_endpoint_response(self):
        storage_attachments = [{
            "data_source_name": "my-bucket",
            "attachments": [{"mode": "awsProfile"}],
        }]
        ep = {
            "metadata": {"name": "ep"},
            "spec": {
                "components": [{
                    "name": "default",
                    "frontend": True,
                    "image": "nginx",
                    "storage_attachments": storage_attachments,
                }]
            },
            "status": {"state": "Ready"},
        }
        legacy = translation.http_endpoint_to_legacy(ep)
        self.assertEqual(legacy["spec"]["storage_attachments"], storage_attachments)


class TestSecureEndpointAuthTranslation(unittest.TestCase):
    # LEP-6218: optional authentication mode has three distinct public states;
    # absent must remain absent, while explicit true and false survive both
    # API-family translations.
    def test_allow_unauthenticated_access_true_false_and_absent_round_trip(self):
        cases = (
            ("absent", None, None),
            ("explicit opt-out", True, []),
            ("explicit protected", False, [{"value": "caller-token"}]),
        )
        for case, allow, tokens in cases:
            with self.subTest(case=case):
                legacy_spec = {
                    "container": {"image": "nginx"},
                    "resource_requirement": {"resource_shape": "cpu.small"},
                }
                if allow is not None:
                    legacy_spec["allow_unauthenticated_access"] = allow
                    legacy_spec["api_tokens"] = tokens
                legacy = {
                    "metadata": {"name": "ep"},
                    "spec": legacy_spec,
                }

                wire = translation.legacy_to_http_endpoint(legacy)
                back = translation.http_endpoint_to_legacy(wire)

                if allow is None:
                    self.assertNotIn(
                        "allow_unauthenticated_access",
                        wire["spec"],
                    )
                    self.assertNotIn(
                        "allow_unauthenticated_access",
                        back["spec"],
                    )
                else:
                    self.assertIs(
                        wire["spec"]["allow_unauthenticated_access"],
                        allow,
                    )
                    self.assertEqual(wire["spec"]["api_tokens"], tokens)
                    self.assertIs(
                        back["spec"]["allow_unauthenticated_access"],
                        allow,
                    )
                    self.assertEqual(back["spec"]["api_tokens"], tokens)

    # LEP-6218: spec-only export/reload retains the explicit mode and token
    # values that file-based CLI creation consumes.
    def test_model_export_reload_preserves_authentication_mode(self):
        cases = (
            (True, []),
            (False, [TokenVar(value="caller-token")]),
        )
        for allow, tokens in cases:
            with self.subTest(allow=allow):
                original = LeptonDeploymentUserSpec(
                    allow_unauthenticated_access=allow,
                    api_tokens=tokens,
                )
                exported = json.loads(
                    original.model_dump_json(by_alias=True, exclude_none=True)
                )
                reloaded = LeptonDeploymentUserSpec(**exported)

                self.assertIs(
                    exported["allow_unauthenticated_access"],
                    allow,
                )
                self.assertIs(reloaded.allow_unauthenticated_access, allow)
                self.assertEqual(
                    [token.value for token in reloaded.api_tokens],
                    [token.value for token in tokens],
                )

        absent = LeptonDeploymentUserSpec()
        self.assertNotIn(
            "allow_unauthenticated_access",
            absent.model_dump(exclude_none=True),
        )

    # LEP-6218: endpoint merge patches carry both fields for mode transitions,
    # but neither field for unrelated changes.
    def test_endpoint_patch_authentication_fields_are_atomic_or_omitted(self):
        protected = {
            "metadata": {"name": "ep"},
            "spec": {
                "components": [{"name": "default", "image": "nginx"}],
                "api_tokens": [{"value": "old-token"}],
                "allow_unauthenticated_access": False,
            },
        }
        opt_out = translation.legacy_to_http_endpoint_patch(
            protected,
            {
                "metadata": {"name": "ep"},
                "spec": {
                    "api_tokens": [],
                    "allow_unauthenticated_access": True,
                },
            },
        )
        self.assertEqual(opt_out["spec"]["api_tokens"], [])
        self.assertIs(opt_out["spec"]["allow_unauthenticated_access"], True)

        unauthenticated = {
            **protected,
            "spec": {
                **protected["spec"],
                "api_tokens": [],
                "allow_unauthenticated_access": True,
            },
        }
        protect = translation.legacy_to_http_endpoint_patch(
            unauthenticated,
            {
                "metadata": {"name": "ep"},
                "spec": {
                    "api_tokens": [{"value": "new-token"}],
                    "allow_unauthenticated_access": False,
                },
            },
        )
        self.assertEqual(
            protect["spec"]["api_tokens"],
            [{"value": "new-token"}],
        )
        self.assertIs(protect["spec"]["allow_unauthenticated_access"], False)

        unrelated = translation.legacy_to_http_endpoint_patch(
            protected,
            {
                "metadata": {"name": "ep"},
                "spec": {"container": {"image": "nginx:new"}},
            },
        )
        self.assertNotIn("api_tokens", unrelated["spec"])
        self.assertNotIn("allow_unauthenticated_access", unrelated["spec"])


class TestPodCompatibilityRegressions(unittest.TestCase):
    def _pod_spec(self):
        return LeptonDeployment(
            metadata=Metadata(name="pod"),
            spec=LeptonDeploymentUserSpec(
                is_pod=True,
                container=LeptonContainer(image="ubuntu"),
                resource_requirement=ResourceRequirement(resource_shape="cpu.small"),
            ),
        )

    def test_deployment_create_with_pod_spec_delegates_to_devpod(self):
        fake = _resource_client()
        calls = []
        fake.pod = SimpleNamespace(create=lambda spec: calls.append(spec) or True)
        api = EndpointAPI(fake)

        spec = self._pod_spec()
        self.assertTrue(api.create(spec))
        self.assertEqual(calls, [spec])

    def test_deprecated_create_pod_delegates_to_devpod(self):
        fake = _resource_client()
        calls = []
        fake.pod = SimpleNamespace(create=lambda spec: calls.append(spec) or True)
        api = EndpointAPI(fake)

        spec = self._pod_spec()
        with self.assertWarns(DeprecationWarning):
            self.assertTrue(api.create_pod(spec))
        self.assertEqual(calls, [spec])

    def test_pod_objects_never_dispatch_to_endpoint_routes(self):
        pod = self._pod_spec()
        pod.metadata.id_ = "pod"

        endpoint_transport = Mock(
            side_effect=AssertionError("pod object reached an /endpoints transport")
        )
        fake = SimpleNamespace(
            _get=endpoint_transport,
            _post=endpoint_transport,
            _put=endpoint_transport,
            _patch=endpoint_transport,
            _delete=endpoint_transport,
            _head=endpoint_transport,
        )
        fake.pod = SimpleNamespace(
            get=Mock(return_value="pod-get"),
            update=Mock(side_effect=RuntimeError("pod updates are unsupported")),
            stop=Mock(return_value="pod-stop"),
            delete=Mock(return_value=True),
            restart=Mock(return_value="pod-restart"),
            get_readiness=Mock(
                side_effect=NewDevPodAPIUnsupported("pod readiness is unsupported")
            ),
            get_termination=Mock(
                side_effect=NewDevPodAPIUnsupported("pod termination is unsupported")
            ),
            get_log=Mock(
                side_effect=NewDevPodAPIUnsupported("pod live logs are unsupported")
            ),
        )
        api = EndpointAPI(fake)

        self.assertEqual(api.get(pod), "pod-get")
        self.assertEqual(api.stop(pod), "pod-stop")
        self.assertTrue(api.delete(pod))
        self.assertEqual(api.restart(pod), "pod-restart")
        with self.assertRaisesRegex(RuntimeError, "pod updates"):
            api.update(pod, pod)
        with self.assertRaises(NewDevPodAPIUnsupported):
            api.get_readiness(pod)
        with self.assertRaises(NewDevPodAPIUnsupported):
            api.get_termination(pod)
        with self.assertRaises(NewEndpointAPIUnsupported):
            api.get_replicas(pod)
        with self.assertRaises(NewDevPodAPIUnsupported):
            list(api.get_log(pod, replica="unused", timeout=7))
        with self.assertRaises(NewEndpointAPIUnsupported):
            api.get_events(pod)

        fake.pod.get.assert_called_once_with(pod)
        fake.pod.update.assert_called_once_with(pod, pod)
        fake.pod.stop.assert_called_once_with(pod)
        fake.pod.delete.assert_called_once_with(pod)
        fake.pod.restart.assert_called_once_with(pod)
        fake.pod.get_readiness.assert_called_once_with(pod)
        fake.pod.get_termination.assert_called_once_with(pod)
        fake.pod.get_log.assert_called_once_with(pod, timeout=7)
        endpoint_transport.assert_not_called()

    def test_devpod_direct_resources_are_rejected_instead_of_dropped(self):
        legacy = self._pod_spec().model_dump(by_alias=True, exclude_none=True)
        legacy["spec"]["resource_requirement"].update({"cpu": 2, "memory": 4096})
        with self.assertRaisesRegex(ValueError, "DevPod API accepts resource_shape"):
            translation.legacy_to_http_devpod(legacy)

    def test_devpod_labels_are_rejected_instead_of_dropped(self):
        legacy = self._pod_spec().model_dump(by_alias=True, exclude_none=True)
        legacy["metadata"]["labels"] = {"team": "inference"}
        with self.assertRaisesRegex(ValueError, "metadata labels"):
            translation.legacy_to_http_devpod(legacy)

    def test_devpod_empty_labels_are_accepted_as_noop(self):
        legacy = self._pod_spec().model_dump(by_alias=True, exclude_none=True)
        legacy["metadata"]["labels"] = {}
        wire = translation.legacy_to_http_devpod(legacy)
        self.assertEqual(wire["metadata"]["name"], "pod")
        self.assertNotIn("labels", wire["metadata"])

    def test_devpod_metadata_id_fallback_and_owner_reach_wire(self):
        legacy = self._pod_spec().model_dump(by_alias=True, exclude_none=True)
        legacy["metadata"] = {"id": "pod-from-id", "owner": "pod-owner"}
        wire = translation.legacy_to_http_devpod(legacy)
        self.assertEqual(
            wire["metadata"],
            {"name": "pod-from-id", "owner": "pod-owner"},
        )

    def test_storage_attachments_reach_devpod_create(self):
        storage_attachments = [{
            "data_source_name": "my-bucket",
            "attachments": [{"mode": "awsProfile"}],
        }]
        legacy = self._pod_spec().model_dump(by_alias=True, exclude_none=True)
        legacy["spec"]["storage_attachments"] = storage_attachments
        wire = translation.legacy_to_http_devpod(legacy)
        self.assertEqual(wire["spec"]["storage_attachments"], storage_attachments)

    def test_storage_attachments_round_trip_from_devpod_response(self):
        storage_attachments = [{
            "data_source_name": "my-bucket",
            "attachments": [{"mode": "awsProfile"}],
        }]
        raw = {
            "metadata": {"name": "pod"},
            "spec": {
                "container": {"image": "ubuntu"},
                "resource_shape": "cpu.small",
                "storage_attachments": storage_attachments,
            },
            "status": {"state": "Running"},
        }
        legacy = translation.http_devpod_to_legacy(raw)
        self.assertEqual(legacy["spec"]["storage_attachments"], storage_attachments)

    def test_devpod_rejects_unsupported_effective_legacy_fields(self):
        unsupported_values = {
            "health": {"readiness": {}},
            "scheduling_policy": {"replica_spread": "Required"},
            "routing_policy": {"enable_header_based_replica_routing": True},
            "auth_config": {"ip_allowlist": ["192.0.2.0/24"]},
            "load_balance_config": {"least_request": {"choice_count": 2}},
        }
        for field, value in unsupported_values.items():
            with self.subTest(field=field):
                legacy = self._pod_spec().model_dump(by_alias=True, exclude_none=True)
                legacy["spec"][field] = value
                with self.assertRaisesRegex(ValueError, field):
                    translation.legacy_to_http_devpod(legacy)

    def test_devpod_status_pairs_only_host_mapped_duplicate_ports(self):
        raw = {
            "metadata": {"name": "pod"},
            "spec": {
                "container": {
                    "image": "ubuntu",
                    "ports": [
                        {
                            "name": "admin",
                            "container_port": 8080,
                            "protocol": "TCP",
                            "expose_strategies": ["HostPortMapping"],
                        },
                        {
                            "name": "web",
                            "container_port": 8080,
                            "protocol": "TCP",
                            "expose_strategies": ["IngressProxy"],
                        },
                        {
                            "name": "dns",
                            "container_port": 8080,
                            "protocol": "UDP",
                            "expose_strategies": ["HostPortMapping"],
                        },
                    ],
                }
            },
            "status": {
                "state": "Ready",
                "port_statuses": [
                    {"container_port": 8080, "host_port": 41000},
                    {"container_port": 8080, "host_port": 41001},
                ],
            },
        }
        legacy = translation.http_devpod_to_legacy(raw)
        statuses = legacy["status"]["container_port_status"]
        self.assertEqual(
            [(p["name"], p["protocol"], p["host_port"]) for p in statuses],
            [("admin", "TCP", 41000), ("dns", "UDP", 41001)],
        )

    def test_missing_devpod_host_port_stays_unknown(self):
        raw = {
            "metadata": {"name": "pod"},
            "spec": {
                "container": {
                    "ports": [{
                        "container_port": 8080,
                        "protocol": "TCP",
                        "expose_strategies": ["HostPortMapping"],
                    }]
                }
            },
            "status": {
                "state": "Starting",
                "port_statuses": [{"container_port": 8080}],
            },
        }
        legacy = translation.http_devpod_to_legacy(raw)
        self.assertNotIn("host_port", legacy["status"]["container_port_status"][0])


class TestObservableCompatibilityRegressions(unittest.TestCase):
    def test_translated_lists_skip_only_malformed_items(self):
        valid_endpoint = {
            "metadata": {"name": "good"},
            "spec": {"components": [{"name": "default", "image": "nginx"}]},
            "status": {"state": "Ready"},
        }
        invalid_endpoint = {
            "metadata": {"name": "bad"},
            "spec": {
                "components": [{"name": "default", "ports": [{"container_port": 0}]}]
            },
            "status": {"state": "Ready"},
        }
        # Put the null first so the test proves a bad entry does not terminate
        # traversal before later valid entries.
        api = EndpointAPI(
            _resource_client(_response([None, invalid_endpoint, valid_endpoint]))
        )
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = api.list_all()
        self.assertEqual([item.metadata.name for item in result], ["good"])
        self.assertIn("Skipped 2 invalid endpoint", stderr.getvalue())

        valid_pod = {
            "metadata": {"name": "good-pod"},
            "spec": {"container": {"image": "ubuntu"}},
            "status": {"state": "Ready"},
        }
        invalid_pod = {
            "metadata": {"name": "bad-pod"},
            "spec": {"container": {"ports": [{"container_port": 0}]}},
            "status": {"state": "Ready"},
        }
        api = DevPodAPI(_resource_client(_response([None, invalid_pod, valid_pod])))
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = api.list_all()
        self.assertEqual([item.metadata.name for item in result], ["good-pod"])
        self.assertIn("Skipped 2 invalid devpod", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
