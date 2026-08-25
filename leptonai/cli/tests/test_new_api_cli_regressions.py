"""CLI regressions for the endpoint/devpod API compatibility dispatcher."""

import io
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

from click.testing import CliRunner
from requests import Response

from leptonai.api.v2.api_resource import ClientError
from leptonai.api.v2.devpod import DevPodAPI
from leptonai.api.v2.endpoint import EndpointAPI
from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.deployment import (
    ContainerPort,
    LeptonContainer,
    LeptonDeployment,
    LeptonDeploymentStatus,
    LeptonDeploymentUserSpec,
    ResourceRequirement,
)
from leptonai.cli.deployment import (
    _create_after_new_api_rerun,
    _print_deployments_table,
    deployment,
)
from leptonai.cli.pod import pod


def _pod(name="pod"):
    return LeptonDeployment(
        metadata=Metadata(id=name, name=name, created_at=1000),
        spec=LeptonDeploymentUserSpec(
            is_pod=True,
            container=LeptonContainer(image="ubuntu"),
            resource_requirement=ResourceRequirement(
                resource_shape="cpu.small", min_replicas=1
            ),
        ),
        status=LeptonDeploymentStatus(
            state="Ready",
            endpoint={"internal_endpoint": "", "external_endpoint": ""},
            container_port_status=None,
            public_ip="203.0.113.7",
        ),
    )


class TestPodSSHMissingPort(unittest.TestCase):
    def test_ready_pod_without_port_status_exits_cleanly(self):
        fake_client = SimpleNamespace(
            pod=SimpleNamespace(get=lambda _name: _pod()),
            get_dashboard_base_url=lambda: None,
        )

        runner = CliRunner()
        with (
            patch("leptonai.cli.pod.APIClient", return_value=fake_client),
            patch(
                "leptonai.cli.pod._get_only_replica_public_ip",
                return_value="203.0.113.7",
            ),
            patch("leptonai.cli.pod.subprocess.run") as run,
        ):
            result = runner.invoke(pod, ["ssh", "--name", "pod"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("SSH port not found", result.output)
        run.assert_not_called()

    def test_list_detail_does_not_render_unallocated_host_port(self):
        pod_model = _pod()
        pod_model.status.container_port_status = [
            ContainerPort(container_port=22, host_port=None)
        ]
        fake_client = SimpleNamespace(
            pod=SimpleNamespace(list_all=lambda: [pod_model]),
            get_dashboard_base_url=lambda: None,
        )

        runner = CliRunner()
        with (
            patch("leptonai.cli.pod.APIClient", return_value=fake_client),
            patch(
                "leptonai.cli.pod._get_only_replica_public_ip",
                return_value="203.0.113.7",
            ),
        ):
            result = runner.invoke(pod, ["list", "--detail"])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("None", result.output)
        self.assertNotIn("ssh -p", result.output)


class TestEndpointListCapacity(unittest.TestCase):
    def test_static_endpoint_uses_configured_target_not_current_readiness(self):
        endpoint_model = LeptonDeployment(
            metadata=Metadata(id="ep", name="ep", created_at=1000),
            spec=LeptonDeploymentUserSpec(
                container=LeptonContainer(image="nginx"),
                resource_requirement=ResourceRequirement(
                    resource_shape="cpu.small", min_replicas=4
                ),
            ),
            status=LeptonDeploymentStatus(
                state="Starting",
                endpoint={"internal_endpoint": "", "external_endpoint": ""},
                ready_replicas=1,
            ),
        )
        tables = []

        class RecordingTable:
            def __init__(self, *args, **kwargs):
                self.rows = []
                tables.append(self)

            def add_column(self, *args, **kwargs):
                pass

            def add_row(self, *values):
                self.rows.append(values)

        with (
            patch("leptonai.cli.deployment.Table", RecordingTable),
            patch("leptonai.cli.deployment.console") as console,
        ):
            _print_deployments_table([endpoint_model])

        self.assertEqual(tables[0].rows[0][5], "4")
        console.print.assert_any_call("  [bright_black]cpu.small[/] : [bold cyan]4[/]")


class TestNotReadyStopBehavior(unittest.TestCase):
    def _workload(self, *, is_pod, state, phase):
        workload = _pod("workload")
        workload.spec.is_pod = is_pod
        workload.status.state = state
        workload.status.phase = phase
        return workload

    def test_endpoint_not_ready_phase_can_still_be_stopped(self):
        workload = self._workload(
            is_pod=False,
            state="Not Ready",
            phase="Not Ready",
        )
        deployment_api = Mock()
        deployment_api.get.return_value = workload
        fake_client = SimpleNamespace(deployment=deployment_api)

        runner = CliRunner()
        with patch("leptonai.cli.deployment.APIClient", return_value=fake_client):
            result = runner.invoke(deployment, ["stop", "--name", "workload"])

        self.assertEqual(result.exit_code, 0, result.output)
        deployment_api.stop.assert_called_once_with("workload")

    def test_pod_not_ready_phase_can_still_be_stopped(self):
        workload = self._workload(
            is_pod=True,
            state="Not Ready",
            phase="Not Ready",
        )
        pod_api = Mock()
        pod_api.get.return_value = workload
        fake_client = SimpleNamespace(pod=pod_api)

        runner = CliRunner()
        with patch("leptonai.cli.pod.APIClient", return_value=fake_client):
            result = runner.invoke(pod, ["stop", "--name", "workload"])

        self.assertEqual(result.exit_code, 0, result.output)
        pod_api.stop.assert_called_once_with("workload")

    def test_phase_absent_not_ready_keeps_legacy_noop(self):
        workload = self._workload(
            is_pod=False,
            state="Not Ready",
            phase=None,
        )
        deployment_api = Mock()
        deployment_api.get.return_value = workload
        fake_client = SimpleNamespace(deployment=deployment_api)

        runner = CliRunner()
        with patch("leptonai.cli.deployment.APIClient", return_value=fake_client):
            result = runner.invoke(deployment, ["stop", "--name", "workload"])

        self.assertEqual(result.exit_code, 0, result.output)
        deployment_api.stop.assert_not_called()


class TestPodFlavouredEndpointCreate(unittest.TestCase):
    def test_rerun_uses_pod_api_and_retries_async_deletion_conflict(self):
        calls = []
        existing = SimpleNamespace(metadata=Metadata(name="pod"))
        conflict_response = Response()
        conflict_response.status_code = 409
        conflict_response._content = b'{"message":"devpod is still deleting"}'
        conflicts = [ClientError(conflict_response)]

        def create_pod(spec):
            calls.append(("pod-create", spec.spec.is_pod))
            if conflicts:
                raise conflicts.pop()
            return True

        def validate_pod(spec):
            calls.append((
                "pod-validate",
                spec.metadata.name,
                spec.spec.container.image,
                spec.spec.container.ports[0].container_port,
                [(env.name, env.value) for env in spec.spec.envs],
            ))

        pod_api = Mock(spec=DevPodAPI)
        pod_api.validate_create.side_effect = validate_pod
        pod_api.list_all.side_effect = lambda: calls.append("pod-list") or [existing]
        pod_api.delete.side_effect = lambda name: calls.append(("pod-delete", name))
        pod_api.create.side_effect = create_pod
        deployment_api = SimpleNamespace(
            list_all=lambda: calls.append("endpoint-list") or [],
            delete=lambda name: calls.append(("endpoint-delete", name)),
            create=lambda spec: calls.append(("endpoint-create", spec.spec.is_pod)),
        )
        fake_client = SimpleNamespace(pod=pod_api, deployment=deployment_api)

        spec = LeptonDeploymentUserSpec(
            is_pod=True,
            container=LeptonContainer(image="ubuntu"),
            resource_requirement=ResourceRequirement(resource_shape="cpu.small"),
        )
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("pod.json", "w") as spec_file:
                spec_file.write(spec.model_dump_json())
            with (
                patch("leptonai.cli.deployment.APIClient", return_value=fake_client),
                patch("leptonai.cli.deployment.time.monotonic", return_value=0),
                patch("leptonai.cli.deployment.time.sleep") as sleep,
            ):
                result = runner.invoke(
                    deployment,
                    [
                        "create",
                        "--name",
                        "pod",
                        "--file",
                        "pod.json",
                        "--container-image",
                        "ubuntu:24.04",
                        "--container-port",
                        "2222",
                        "--env",
                        "MODE=pod-rerun",
                        "--rerun",
                    ],
                )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(
            calls,
            [
                (
                    "pod-validate",
                    "pod",
                    "ubuntu:24.04",
                    2222,
                    [("MODE", "pod-rerun")],
                ),
                "pod-list",
                ("pod-delete", "pod"),
                ("pod-create", True),
                ("pod-create", True),
            ],
        )
        sleep.assert_called_once_with(0.5)


class TestNewEndpointRerun(unittest.TestCase):
    def test_non_rerun_duplicate_exits_before_mutation_or_validation(self):
        existing = SimpleNamespace(metadata=Metadata(name="ep"))
        endpoint_api = Mock(spec=EndpointAPI)
        endpoint_api.list_all.return_value = [existing]
        fake_client = SimpleNamespace(
            deployment=endpoint_api,
            pod=SimpleNamespace(),
        )

        class TTYInput(io.BytesIO):
            def isatty(self):
                return True

        runner = CliRunner()
        with (
            patch("leptonai.cli.deployment.APIClient", return_value=fake_client),
            patch(
                "leptonai.cli.deployment._create_workspace_token_secret_var_if_not_existing"
            ) as create_workspace_token_secret,
            patch(
                "leptonai.cli.deployment.click.confirm", return_value=True
            ) as confirm,
        ):
            result = runner.invoke(
                deployment,
                [
                    "create",
                    "--name",
                    "ep",
                    "--container-image",
                    "nginx:1.27",
                    "--include-workspace-token",
                ],
                input=TTYInput(),
            )

        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("already exists", result.output)
        endpoint_api.list_all.assert_called_once_with()
        create_workspace_token_secret.assert_not_called()
        confirm.assert_not_called()
        endpoint_api.validate_create.assert_not_called()
        endpoint_api.delete.assert_not_called()
        endpoint_api.create.assert_not_called()

    def test_rerun_validates_fully_assembled_spec_before_list_and_delete(self):
        calls = []
        existing = SimpleNamespace(metadata=Metadata(name="ep"))

        def validate_endpoint(spec):
            calls.append((
                "endpoint-validate",
                spec.metadata.name,
                spec.spec.container.image,
                spec.spec.container.ports[0].container_port,
                [(env.name, env.value) for env in spec.spec.envs],
            ))

        def create_endpoint(spec, *, tolerate_legacy_response):
            calls.append((
                "endpoint-create",
                spec.spec.is_pod,
                tolerate_legacy_response,
            ))
            return True

        endpoint_api = Mock(spec=EndpointAPI)
        endpoint_api.validate_create.side_effect = validate_endpoint
        endpoint_api.list_all.side_effect = lambda: calls.append("endpoint-list") or [
            existing
        ]
        endpoint_api.delete.side_effect = lambda name: calls.append(
            ("endpoint-delete", name)
        )
        endpoint_api.create_with_response.side_effect = create_endpoint
        fake_client = SimpleNamespace(
            deployment=endpoint_api,
            pod=SimpleNamespace(),
        )
        spec = LeptonDeploymentUserSpec(
            is_pod=False,
            container=LeptonContainer(image="nginx:old"),
            resource_requirement=ResourceRequirement(resource_shape="cpu.small"),
        )

        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("endpoint.json", "w") as spec_file:
                spec_file.write(spec.model_dump_json())
            with patch("leptonai.cli.deployment.APIClient", return_value=fake_client):
                result = runner.invoke(
                    deployment,
                    [
                        "create",
                        "--name",
                        "ep",
                        "--file",
                        "endpoint.json",
                        "--container-image",
                        "nginx:1.27",
                        "--container-port",
                        "8080:tcp",
                        "--env",
                        "MODE=endpoint-rerun",
                        "--rerun",
                    ],
                )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(
            calls,
            [
                (
                    "endpoint-validate",
                    "ep",
                    "nginx:1.27",
                    8080,
                    [("MODE", "endpoint-rerun")],
                ),
                "endpoint-list",
                ("endpoint-delete", "ep"),
                ("endpoint-create", False, True),
            ],
        )
        endpoint_api.create.assert_not_called()

    def test_validation_failure_does_not_list_delete_or_create(self):
        cases = [
            ("endpoint", False, EndpointAPI),
            ("pod", True, DevPodAPI),
        ]

        for name, is_pod, api_class in cases:
            with self.subTest(name=name):
                calls = []

                def reject(spec):
                    calls.append((
                        "validate",
                        spec.metadata.name,
                        spec.spec.container.image,
                        spec.spec.container.ports[0].container_port,
                        [(env.name, env.value) for env in spec.spec.envs],
                    ))
                    raise ValueError("replacement cannot be translated")

                selected_api = Mock(spec=api_class)
                selected_api.validate_create.side_effect = reject
                fake_client = SimpleNamespace(
                    deployment=selected_api if not is_pod else SimpleNamespace(),
                    pod=selected_api if is_pod else SimpleNamespace(),
                )
                spec = LeptonDeploymentUserSpec(
                    is_pod=is_pod,
                    container=LeptonContainer(image="original:image"),
                    resource_requirement=ResourceRequirement(
                        resource_shape="cpu.small"
                    ),
                )

                runner = CliRunner()
                with runner.isolated_filesystem():
                    with open("spec.json", "w") as spec_file:
                        spec_file.write(spec.model_dump_json())
                    with patch(
                        "leptonai.cli.deployment.APIClient",
                        return_value=fake_client,
                    ):
                        result = runner.invoke(
                            deployment,
                            [
                                "create",
                                "--name",
                                name,
                                "--file",
                                "spec.json",
                                "--container-image",
                                "assembled:image",
                                "--container-port",
                                "4242",
                                "--env",
                                "MODE=preflight",
                                "--rerun",
                            ],
                        )

                self.assertEqual(result.exit_code, 1, result.output)
                self.assertEqual(
                    calls,
                    [(
                        "validate",
                        name,
                        "assembled:image",
                        4242,
                        [("MODE", "preflight")],
                    )],
                )
                selected_api.list_all.assert_not_called()
                selected_api.delete.assert_not_called()
                selected_api.create.assert_not_called()

    def test_create_retries_conflict_until_async_delete_finishes(self):
        conflicts = []
        for _ in range(2):
            response = Response()
            response.status_code = 409
            response._content = b'{"message":"endpoint is still deleting"}'
            conflicts.append(ClientError(response))

        attempts = []

        def create(spec):
            attempts.append(spec)
            if conflicts:
                raise conflicts.pop(0)
            return True

        spec = object()
        with (
            patch("leptonai.cli.deployment.time.monotonic", return_value=0),
            patch("leptonai.cli.deployment.time.sleep") as sleep,
        ):
            result = _create_after_new_api_rerun(
                SimpleNamespace(create=create), spec, "ep"
            )

        self.assertTrue(result)
        self.assertEqual(attempts, [spec, spec, spec])
        self.assertEqual(sleep.call_count, 2)


if __name__ == "__main__":
    unittest.main()
