"""Pure-function tests for the Dynamo spec builders and merge-patch helpers."""

import os
import tempfile
import unittest

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

from leptonai.api.v2.dynamo_patch import (
    apply_merge_patch,
    build_merge_patch,
    deep_merge_patch,
    spec_to_dict,
)
from leptonai.api.v2.dynamo_spec import (
    DYNAMO_VERSION,
    DynamoServiceInput,
    build_dynamo_spec,
    build_service_spec,
    command_display_string,
    get_default_command,
    get_default_image,
    get_default_working_dir,
    serving_mode_from_services,
    shell_command_argv,
    sort_service_names,
    validate_dynamo_name,
    validate_framework_and_mode,
)
from leptonai.api.v2.types.dynamo import (
    DYNAMO_WORKER_ROLE_LABEL_KEY,
    LeptonDynamoGraphDeploymentUserSpec,
)


def _frontend(**overrides):
    kwargs = dict(name="frontend", resource_shape="cpu.small", node_groups=["ng-1"])
    kwargs.update(overrides)
    return DynamoServiceInput(**kwargs)


class TestDefaultsRegistry(unittest.TestCase):
    def test_default_image_uses_framework_and_version(self):
        self.assertEqual(
            get_default_image("vllm"),
            f"nvcr.io/nvidia/ai-dynamo/vllm-runtime:{DYNAMO_VERSION}",
        )
        self.assertEqual(
            get_default_image("trtllm", "1.3.1"),
            "nvcr.io/nvidia/ai-dynamo/tensorrtllm-runtime:1.3.1",
        )
        with self.assertRaises(ValueError):
            get_default_image("tgi")

    def test_default_working_dir(self):
        self.assertEqual(get_default_working_dir("sglang", "frontend"), "/workspace")
        self.assertEqual(
            get_default_working_dir("sglang", "worker"),
            "/workspace/examples/backends/sglang",
        )
        self.assertEqual(
            get_default_working_dir("trtllm", "decode-worker"), "/workspace/"
        )

    def test_default_commands(self):
        self.assertEqual(
            get_default_command("vllm", "frontend", "aggregated"),
            "python3 -m dynamo.frontend",
        )
        self.assertEqual(
            get_default_command("vllm", "worker", "aggregated"),
            "python3 -m dynamo.vllm --model Qwen/Qwen3-0.6B",
        )
        self.assertIn(
            "--disaggregation-mode decode",
            get_default_command("trtllm", "decode-worker", "disaggregated"),
        )
        # Unknown combinations yield an empty command rather than raising.
        self.assertEqual(get_default_command("vllm", "worker", "disaggregated"), "")

    def test_sglang_multinode_command_rewrite(self):
        aggregated = get_default_command(
            "sglang", "worker", "aggregated", node_count=2, gpu_count=4
        )
        self.assertIn("--tp 8", aggregated)
        self.assertNotIn("--tp 1", aggregated)

        disaggregated = get_default_command(
            "sglang", "prefill-worker", "disaggregated", node_count=2, gpu_count=4
        )
        self.assertIn("--tp-size 8", disaggregated)
        self.assertIn("--disaggregation-bootstrap-port 30001", disaggregated)
        self.assertTrue(disaggregated.endswith(" --mem-fraction-static 0.82"))

        # vLLM/TensorRT-LLM never rewrite, and the frontend never does.
        self.assertEqual(
            get_default_command("vllm", "worker", "aggregated", node_count=2),
            get_default_command("vllm", "worker", "aggregated"),
        )
        self.assertEqual(
            get_default_command("sglang", "frontend", "aggregated", node_count=2),
            "python3 -m dynamo.frontend",
        )

    def test_shell_command_argv_round_trip(self):
        argv = shell_command_argv("python3 -m dynamo.frontend")
        self.assertEqual(argv, ["/bin/sh", "-c", "python3 -m dynamo.frontend"])
        self.assertIsNone(shell_command_argv("   "))
        self.assertIsNone(shell_command_argv(None))
        self.assertEqual(command_display_string(argv), "python3 -m dynamo.frontend")
        self.assertEqual(
            command_display_string(["python3", "-m", "x y"]), "python3 -m 'x y'"
        )
        self.assertEqual(command_display_string(None), "")

    def test_serving_mode_and_sorting(self):
        self.assertEqual(
            serving_mode_from_services(["frontend", "worker"]), "aggregated"
        )
        self.assertEqual(
            serving_mode_from_services(["decode-worker", "frontend"]), "disaggregated"
        )
        self.assertEqual(
            sort_service_names(["worker", "frontend", "decode-worker"]),
            ["frontend", "decode-worker", "worker"],
        )


class TestValidation(unittest.TestCase):
    def test_name_rules(self):
        self.assertEqual(validate_dynamo_name("my-dynamo-1"), "my-dynamo-1")
        for bad in ("", "a" * 37, "Upper", "1abc", "abc-", "foo-by-lepton"):
            with self.assertRaises(ValueError, msg=bad):
                validate_dynamo_name(bad)

    def test_vllm_rejects_disaggregated(self):
        with self.assertRaises(ValueError):
            validate_framework_and_mode("vllm", "disaggregated")
        validate_framework_and_mode("sglang", "disaggregated")
        with self.assertRaises(ValueError):
            validate_framework_and_mode("vllm", "hybrid")


class TestBuildDynamoSpec(unittest.TestCase):
    def test_single_frontend_matches_dashboard_user_story(self):
        spec = build_dynamo_spec(services=[_frontend(node_groups=["default"])])

        self.assertEqual(spec.backend_framework, "vllm")
        self.assertEqual(spec.dynamo_version, "1.3.1")
        self.assertTrue(spec.ingress_enabled)
        self.assertIsNone(spec.dynamo_namespace)
        self.assertEqual(list(spec.services), ["frontend"])

        frontend = spec.services["frontend"]
        self.assertEqual(frontend.component_type, "frontend")
        self.assertEqual(frontend.resource_shape, "cpu.small")
        self.assertEqual(frontend.min_replicas, 1)
        self.assertEqual(frontend.affinity.allowed_dedicated_node_groups, ["default"])
        container = frontend.extra_pod_spec.main_container
        self.assertEqual(container.image, "nvcr.io/nvidia/ai-dynamo/vllm-runtime:1.3.1")
        self.assertEqual(container.working_dir, "/workspace")
        self.assertEqual(
            container.command, ["/bin/sh", "-c", "python3 -m dynamo.frontend"]
        )
        self.assertEqual(frontend.extra_pod_metadata.annotations, {})
        self.assertEqual(frontend.extra_pod_metadata.labels, {})

    def test_aggregated_worker_inherits_node_group(self):
        spec = build_dynamo_spec(
            services=[
                _frontend(node_groups=["ng-gpu-a10"]),
                DynamoServiceInput(
                    name="worker",
                    resource_shape="gpu.a100-1",
                    replicas=2,
                    envs=["MODEL_NAME=Qwen/Qwen3-0.6B"],
                    secrets=["HF_TOKEN=my-secret"],
                ),
            ]
        )
        worker = spec.services["worker"]
        self.assertEqual(worker.component_type, "worker")
        self.assertEqual(worker.min_replicas, 2)
        self.assertEqual(worker.affinity.allowed_dedicated_node_groups, ["ng-gpu-a10"])
        container = worker.extra_pod_spec.main_container
        self.assertEqual(container.working_dir, "/workspace/examples/backends/vllm")
        self.assertEqual(
            container.command,
            ["/bin/sh", "-c", "python3 -m dynamo.vllm --model Qwen/Qwen3-0.6B"],
        )
        self.assertEqual(worker.envs[0].name, "MODEL_NAME")
        self.assertEqual(worker.envs[0].value, "Qwen/Qwen3-0.6B")
        self.assertEqual(worker.envs[1].value_from.secret_name_ref, "my-secret")
        self.assertNotIn(DYNAMO_WORKER_ROLE_LABEL_KEY, worker.extra_pod_metadata.labels)

    def test_disaggregated_workers_get_role_labels(self):
        spec = build_dynamo_spec(
            framework="sglang",
            serving_mode="disaggregated",
            services=[
                _frontend(),
                DynamoServiceInput(name="prefill-worker", resource_shape="gpu.h100-1"),
                DynamoServiceInput(
                    name="decode-worker",
                    resource_shape="gpu.h100-1",
                    labels=["tier=compute", f"{DYNAMO_WORKER_ROLE_LABEL_KEY}=bogus"],
                    annotations=["app=dynamo"],
                ),
            ],
        )
        self.assertEqual(
            list(spec.services), ["frontend", "decode-worker", "prefill-worker"]
        )
        prefill = spec.services["prefill-worker"]
        decode = spec.services["decode-worker"]
        self.assertEqual(
            prefill.extra_pod_metadata.labels, {DYNAMO_WORKER_ROLE_LABEL_KEY: "prefill"}
        )
        self.assertEqual(
            decode.extra_pod_metadata.labels,
            {"tier": "compute", DYNAMO_WORKER_ROLE_LABEL_KEY: "decode"},
        )
        self.assertEqual(decode.extra_pod_metadata.annotations, {"app": "dynamo"})
        self.assertIn(
            "--disaggregation-mode prefill",
            prefill.extra_pod_spec.main_container.command[2],
        )

    def test_global_envs_and_secrets(self):
        spec = build_dynamo_spec(
            services=[_frontend()],
            envs=["MODEL_NAME=Qwen/Qwen3-0.6B"],
            secrets=["HF_TOKEN=my-secret", "OTHER"],
        )
        payload = spec_to_dict(spec)["envs"]
        self.assertEqual(
            payload,
            [
                {"name": "MODEL_NAME", "value": "Qwen/Qwen3-0.6B"},
                {"name": "HF_TOKEN", "value_from": {"secret_name_ref": "my-secret"}},
                {"name": "OTHER", "value_from": {"secret_name_ref": "OTHER"}},
            ],
        )

    def test_multinode_only_for_sglang_workers(self):
        spec = build_dynamo_spec(
            framework="sglang",
            services=[
                _frontend(),
                DynamoServiceInput(
                    name="worker",
                    resource_shape="gpu.h100-8",
                    node_count=2,
                    gpu_count=8,
                ),
            ],
        )
        worker = spec.services["worker"]
        self.assertEqual(worker.multinode.node_count, 2)
        self.assertIn("--tp 16", worker.extra_pod_spec.main_container.command[2])

        with self.assertRaisesRegex(ValueError, "only supported for SGLang"):
            build_dynamo_spec(
                framework="vllm",
                services=[
                    _frontend(),
                    DynamoServiceInput(
                        name="worker", resource_shape="gpu.a10", node_count=2
                    ),
                ],
            )
        with self.assertRaisesRegex(ValueError, "not the frontend"):
            build_dynamo_spec(framework="sglang", services=[_frontend(node_count=2)])
        with self.assertRaisesRegex(ValueError, "at least 2"):
            build_dynamo_spec(
                framework="sglang",
                services=[
                    _frontend(),
                    DynamoServiceInput(
                        name="worker", resource_shape="gpu.a10", node_count=1
                    ),
                ],
            )

    def test_rejections(self):
        with self.assertRaisesRegex(ValueError, "frontend service is required"):
            build_dynamo_spec(
                services=[DynamoServiceInput(name="worker", resource_shape="gpu.a10")]
            )
        with self.assertRaisesRegex(ValueError, "requires --node-group"):
            build_dynamo_spec(services=[_frontend(node_groups=None)])
        with self.assertRaisesRegex(ValueError, "requires --resource-shape"):
            build_dynamo_spec(services=[_frontend(resource_shape=None)])
        with self.assertRaisesRegex(ValueError, "not supported for vLLM"):
            build_dynamo_spec(serving_mode="disaggregated", services=[_frontend()])
        with self.assertRaisesRegex(ValueError, "not available in aggregated mode"):
            build_dynamo_spec(
                framework="sglang",
                services=[
                    _frontend(),
                    DynamoServiceInput(name="prefill-worker", resource_shape="gpu.a10"),
                ],
            )
        with self.assertRaisesRegex(ValueError, "not available in disaggregated mode"):
            build_dynamo_spec(
                framework="sglang",
                serving_mode="disaggregated",
                services=[
                    _frontend(),
                    DynamoServiceInput(name="worker", resource_shape="gpu.a10"),
                ],
            )
        with self.assertRaisesRegex(ValueError, "Unknown Dynamo service"):
            build_dynamo_spec(
                services=[
                    _frontend(),
                    DynamoServiceInput(name="planner", resource_shape="x"),
                ]
            )
        with self.assertRaisesRegex(ValueError, "more than once"):
            build_dynamo_spec(services=[_frontend(), _frontend()])
        with self.assertRaisesRegex(ValueError, "Replicas must be at least 1"):
            build_dynamo_spec(services=[_frontend(replicas=0)])
        with self.assertRaisesRegex(ValueError, "synchronized with the frontend"):
            build_dynamo_spec(
                services=[
                    _frontend(),
                    DynamoServiceInput(
                        name="worker", resource_shape="gpu.a10", node_groups=["ng-2"]
                    ),
                ]
            )
        with self.assertRaisesRegex(ValueError, "ingress_timeout_seconds"):
            build_dynamo_spec(services=[_frontend()], ingress_timeout_seconds=10)
        with self.assertRaisesRegex(ValueError, "annotation value"):
            build_dynamo_spec(services=[_frontend(annotations=["app="])])
        with self.assertRaisesRegex(ValueError, "Invalid environment definition"):
            build_dynamo_spec(services=[_frontend(envs=["NOEQUALS"])])

    def test_ingress_flags(self):
        spec = build_dynamo_spec(
            services=[_frontend()], ingress_enabled=False, ingress_timeout_seconds=600
        )
        self.assertFalse(spec.ingress_enabled)
        self.assertEqual(spec.ingress_timeout_seconds, 600)

    def _base_spec(self):
        return build_dynamo_spec(
            framework="sglang",
            services=[
                _frontend(),
                DynamoServiceInput(
                    name="worker",
                    resource_shape="gpu.h100-8",
                    replicas=2,
                    node_count=2,
                    command="python3 -m custom",
                ),
            ],
        )

    def test_base_spec_overrides_keep_file_values(self):
        base = self._base_spec()
        spec = build_dynamo_spec(
            services=[DynamoServiceInput(name="worker", replicas=3)], base=base
        )
        worker = spec.services["worker"]
        self.assertEqual(spec.backend_framework, "sglang")
        self.assertEqual(worker.min_replicas, 3)
        self.assertEqual(worker.resource_shape, "gpu.h100-8")
        self.assertEqual(worker.multinode.node_count, 2)
        self.assertEqual(
            worker.extra_pod_spec.main_container.command[2], "python3 -m custom"
        )
        # The frontend and its node group come from the file untouched.
        self.assertEqual(
            spec.services["frontend"].affinity.allowed_dedicated_node_groups, ["ng-1"]
        )

    def test_framework_change_cascades_like_the_dashboard(self):
        base = self._base_spec()
        spec = build_dynamo_spec(services=[], framework="trtllm", base=base)
        worker = spec.services["worker"]
        self.assertIsNone(worker.multinode)
        container = worker.extra_pod_spec.main_container
        self.assertEqual(
            container.image, "nvcr.io/nvidia/ai-dynamo/tensorrtllm-runtime:1.3.1"
        )
        self.assertEqual(container.working_dir, "/workspace/")
        self.assertIn("dynamo.trtllm", container.command[2])
        self.assertEqual(
            spec.services["frontend"].extra_pod_spec.main_container.image,
            "nvcr.io/nvidia/ai-dynamo/tensorrtllm-runtime:1.3.1",
        )

    def test_base_spec_with_namespace_is_rejected(self):
        base = self._base_spec()
        base.dynamo_namespace = "prod"
        with self.assertRaisesRegex(ValueError, "dynamo_namespace"):
            build_dynamo_spec(services=[], base=base)

    def test_update_mode_only_touches_given_fields(self):
        base = self._base_spec().services["worker"]
        base.extra_pod_metadata = None
        updated = build_service_spec(
            DynamoServiceInput(name="worker", replicas=5),
            framework="sglang",
            serving_mode="aggregated",
            base=base,
            fill_defaults=False,
        )
        self.assertEqual(updated.min_replicas, 5)
        self.assertIsNone(updated.extra_pod_metadata)
        self.assertEqual(
            spec_to_dict(updated)["extra_pod_spec"],
            spec_to_dict(base)["extra_pod_spec"],
        )
        with self.assertRaisesRegex(ValueError, "at least 1"):
            build_service_spec(
                DynamoServiceInput(name="worker", replicas=0),
                framework="sglang",
                serving_mode="aggregated",
                base=base,
                fill_defaults=False,
            )


class TestMergePatch(unittest.TestCase):
    def test_no_change_is_empty(self):
        original = {"a": 1, "b": {"c": [1, 2]}}
        self.assertEqual(build_merge_patch(original, dict(original)), {})

    def test_changes_removals_and_additions(self):
        original = {
            "ingress_enabled": True,
            "envs": [{"name": "A", "value": "1"}],
            "services": {
                "frontend": {
                    "min_replicas": 1,
                    "extra_pod_spec": {"main_container": {"working_dir": "/w"}},
                },
                "worker": {"min_replicas": 2},
            },
        }
        desired = {
            "ingress_enabled": False,
            "display_name": "hello",
            "envs": [{"name": "A", "value": "2"}],
            "services": {
                "frontend": {
                    "min_replicas": 1,
                    "extra_pod_spec": {"main_container": {}},
                },
            },
        }
        patch = build_merge_patch(original, desired)
        self.assertEqual(
            patch,
            {
                "ingress_enabled": False,
                "display_name": "hello",
                "envs": [{"name": "A", "value": "2"}],
                "services": {
                    "frontend": {
                        "extra_pod_spec": {"main_container": {"working_dir": None}}
                    },
                    "worker": None,
                },
            },
        )
        self.assertEqual(apply_merge_patch(original, patch), desired)

    def test_deep_merge_override_wins(self):
        base = {"spec": {"services": {"worker": {"min_replicas": 3}}}}
        override = {"spec": {"services": {"worker": None}, "display_name": "x"}}
        self.assertEqual(
            deep_merge_patch(base, override),
            {"spec": {"services": {"worker": None}, "display_name": "x"}},
        )

    def test_spec_to_dict_drops_none_and_uses_aliases(self):
        spec = build_dynamo_spec(
            services=[_frontend(mounts=["/data:/mnt/data:node-nfs:my-nfs"])]
        )
        payload = spec_to_dict(spec)
        self.assertNotIn("dynamo_namespace", payload)
        mount = payload["services"]["frontend"]["mounts"][0]
        self.assertEqual(mount["from"], "node-nfs:my-nfs")
        self.assertNotIn("from_", mount)
        self.assertIsInstance(
            LeptonDynamoGraphDeploymentUserSpec.model_validate(payload),
            LeptonDynamoGraphDeploymentUserSpec,
        )


if __name__ == "__main__":
    unittest.main()
