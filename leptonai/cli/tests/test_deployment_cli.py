import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from loguru import logger

from leptonai import config
from leptonai.api.v2.api_resource import ClientError
from leptonai.api.v2.types.affinity import LeptonResourceAffinity
from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.deployment import (
    LeptonDeployment,
    LeptonDeploymentStatus,
    LeptonDeploymentUserSpec,
    ResourceRequirement,
)
from leptonai.cli import lep as cli
from leptonai.cli.deployment import _filter_endpoints, console as deployment_console


logger.info(f"Using cache dir: {config.CACHE_DIR}")


class _FakeDeploymentAPI:
    def __init__(self):
        self.created_spec = None

    def list_all(self):
        return []

    def create(self, spec):
        self.created_spec = spec
        return True


class _FakeAPIClient:
    last_instance = None

    def __init__(self, *args, **kwargs):
        self.deployment = _FakeDeploymentAPI()
        _FakeAPIClient.last_instance = self


class _FakeResponse:
    """Minimal stand-in for a requests.Response used to build ClientError."""

    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


def _make_existing_deployment(name="test-endpoint"):
    """A bare endpoint as returned by client.deployment.get().

    metadata.semantic_version defaults to None, so the update command skips the
    dryrun/rolling-restart branch and goes straight to the real update call.
    """
    return LeptonDeployment(
        metadata=Metadata(id=name, name=name),
        spec=LeptonDeploymentUserSpec(),
    )


class TestDeploymentCliLocal(unittest.TestCase):
    def test_deployment_local(self):
        runner = CliRunner()

        # missing required --name option
        result = runner.invoke(cli, ["deployment", "list"])
        self.assertNotEqual(result.exit_code, 0)
        # self.assertIn("It seems that you are not logged in", result.output)

    def test_deployment_create_parses_protocol_from_container_port(self):
        runner = CliRunner()

        with patch("leptonai.cli.deployment.APIClient", _FakeAPIClient):
            result = runner.invoke(
                cli,
                [
                    "deployment",
                    "create",
                    "--name",
                    "test-endpoint",
                    "--container-image",
                    "nginx:latest",
                    "--container-command",
                    "python -m http.server 8080",
                    "--container-port",
                    "8080:tcp",
                    "--resource-shape",
                    config.DEFAULT_RESOURCE_SHAPE,
                    "--public",
                ],
            )

        self.assertEqual(result.exit_code, 0, result.output)
        created = _FakeAPIClient.last_instance.deployment.created_spec
        self.assertIsNotNone(created)
        self.assertEqual(created.spec.container.ports[0].container_port, 8080)
        self.assertEqual(created.spec.container.ports[0].protocol, "TCP")

    def test_deployment_create_port_only_leaves_protocol_unset(self):
        runner = CliRunner()

        with patch("leptonai.cli.deployment.APIClient", _FakeAPIClient):
            result = runner.invoke(
                cli,
                [
                    "deployment",
                    "create",
                    "--name",
                    "test-endpoint",
                    "--container-image",
                    "nginx:latest",
                    "--container-command",
                    "python -m http.server 8080",
                    "--container-port",
                    "8080",
                    "--resource-shape",
                    config.DEFAULT_RESOURCE_SHAPE,
                    "--public",
                ],
            )

        self.assertEqual(result.exit_code, 0, result.output)
        created = _FakeAPIClient.last_instance.deployment.created_spec
        self.assertIsNotNone(created)
        self.assertEqual(created.spec.container.ports[0].container_port, 8080)
        self.assertIsNone(created.spec.container.ports[0].protocol)

    def test_endpoint_create_rejects_named_mount_without_storage_name(self):
        runner = CliRunner()
        _FakeAPIClient.last_instance = None

        with patch("leptonai.cli.deployment.APIClient", _FakeAPIClient):
            result = runner.invoke(
                cli,
                [
                    "endpoint",
                    "create",
                    "--name",
                    "test-endpoint",
                    "--container-image",
                    "nginx:latest",
                    "--container-command",
                    "python -m http.server 8080",
                    "--resource-shape",
                    config.DEFAULT_RESOURCE_SHAPE,
                    "--public",
                    "--mount",
                    "/hf-cache:/root/.cache/huggingface:node-nfs",
                ],
            )

        self.assertEqual(result.exit_code, 1, result.output)
        output = " ".join(((result.output or "") + (result.stderr or "")).split())
        self.assertIn("Error parsing --mount", output)
        self.assertIn("missing storage_name", output)
        self.assertIn("node-nfs:my-nfs", output)
        self.assertIsNotNone(_FakeAPIClient.last_instance)
        self.assertIsNone(_FakeAPIClient.last_instance.deployment.created_spec)

    def test_endpoint_create_builds_storage_attachments(self):
        runner = CliRunner()
        _FakeAPIClient.last_instance = None

        with patch("leptonai.cli.deployment.APIClient", _FakeAPIClient):
            result = runner.invoke(
                cli,
                [
                    "endpoint",
                    "create",
                    "--name",
                    "test-endpoint",
                    "--container-image",
                    "nginx:latest",
                    "--container-command",
                    "python -m http.server 8080",
                    "--resource-shape",
                    config.DEFAULT_RESOURCE_SHAPE,
                    "--public",
                    "--storage-attachment",
                    "my-bucket:awsProfile",
                    "--storage-attachment",
                    "my-bucket:mscProfile:object.aistore:my-profile",
                ],
            )

        self.assertEqual(result.exit_code, 0, result.output)
        created = _FakeAPIClient.last_instance.deployment.created_spec
        self.assertIsNotNone(created)
        attachments = created.spec.storage_attachments
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].data_source_name, "my-bucket")
        self.assertEqual(len(attachments[0].attachments), 2)
        self.assertEqual(attachments[0].attachments[0].mode, "awsProfile")
        self.assertIsNone(attachments[0].attachments[0].attach_with)
        self.assertEqual(attachments[0].attachments[1].mode, "mscProfile")
        self.assertEqual(attachments[0].attachments[1].attach_with, "object.aistore")
        self.assertEqual(attachments[0].attachments[1].profile_name, "my-profile")

    def test_endpoint_create_rejects_invalid_storage_attachment_mode(self):
        runner = CliRunner()
        _FakeAPIClient.last_instance = None

        with patch("leptonai.cli.deployment.APIClient", _FakeAPIClient):
            result = runner.invoke(
                cli,
                [
                    "endpoint",
                    "create",
                    "--name",
                    "test-endpoint",
                    "--container-image",
                    "nginx:latest",
                    "--container-command",
                    "python -m http.server 8080",
                    "--resource-shape",
                    config.DEFAULT_RESOURCE_SHAPE,
                    "--public",
                    "--storage-attachment",
                    "my-bucket:not-a-mode",
                ],
            )

        self.assertEqual(result.exit_code, 1, result.output)
        output = " ".join(((result.output or "") + (result.stderr or "")).split())
        self.assertIn("Error parsing --storage-attachment", output)
        self.assertIn("MODE must be one of", output)
        self.assertIsNotNone(_FakeAPIClient.last_instance)
        self.assertIsNone(_FakeAPIClient.last_instance.deployment.created_spec)


class TestHeaderBasedRoutingValidation(unittest.TestCase):
    """Issue #3: --header-based-routing parses as a boolean and rejects typos."""

    _CREATE_ARGS = [
        "endpoint",
        "create",
        "--name",
        "test-endpoint",
        "--container-image",
        "nginx:latest",
        "--container-command",
        "python -m http.server 8080",
        "--resource-shape",
        config.DEFAULT_RESOURCE_SHAPE,
        "--public",
    ]

    def _create_with_routing(self, *routing_args):
        _FakeAPIClient.last_instance = None
        with patch("leptonai.cli.deployment.APIClient", _FakeAPIClient):
            return CliRunner().invoke(cli, self._CREATE_ARGS + list(routing_args))

    def test_create_true_enables_routing(self):
        result = self._create_with_routing("--header-based-routing", "true")
        self.assertEqual(result.exit_code, 0, result.output)
        created = _FakeAPIClient.last_instance.deployment.created_spec
        self.assertTrue(created.spec.routing_policy.enable_header_based_replica_routing)

    def test_create_false_disables_routing(self):
        result = self._create_with_routing("--header-based-routing", "false")
        self.assertEqual(result.exit_code, 0, result.output)
        created = _FakeAPIClient.last_instance.deployment.created_spec
        self.assertFalse(
            created.spec.routing_policy.enable_header_based_replica_routing
        )

    def test_create_value_is_case_insensitive(self):
        result = self._create_with_routing("--header-based-routing", "TRUE")
        self.assertEqual(result.exit_code, 0, result.output)
        created = _FakeAPIClient.last_instance.deployment.created_spec
        self.assertTrue(created.spec.routing_policy.enable_header_based_replica_routing)

    def test_create_bare_flag_enables_routing(self):
        # No value given -> flag_value=True kicks in.
        result = self._create_with_routing("--header-based-routing")
        self.assertEqual(result.exit_code, 0, result.output)
        created = _FakeAPIClient.last_instance.deployment.created_spec
        self.assertTrue(created.spec.routing_policy.enable_header_based_replica_routing)

    def test_create_rejects_invalid_value(self):
        # A typo like "ture" must error out, not be silently treated as false.
        result = self._create_with_routing("--header-based-routing", "ture")
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("is not a valid boolean", result.output)
        # Validation fails at parse time, so the client is never constructed.
        self.assertIsNone(_FakeAPIClient.last_instance)

    def test_update_rejects_invalid_value(self):
        # The same validation is wired on the update command.
        with patch("leptonai.cli.deployment.APIClient") as MockClient:
            result = CliRunner().invoke(
                cli,
                [
                    "endpoint",
                    "update",
                    "-n",
                    "test-endpoint",
                    "--header-based-routing",
                    "abc",
                ],
            )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("is not a valid boolean", result.output)
        # Validation happens at parse time, before the client is ever used.
        MockClient.assert_not_called()


class TestEndpointUpdateNoOp(unittest.TestCase):
    """Issue #2: an unchanged value yields a clear message, not a raw 400."""

    def test_no_op_update_reports_clearly_and_exits_zero(self):
        no_op_error = ClientError(
            _FakeResponse(
                400, '{"code":"InvalidRequest","message":"no valid field to update"}'
            )
        )
        with patch("leptonai.cli.deployment.APIClient") as MockClient:
            client = MockClient.return_value
            client.deployment.get.return_value = _make_existing_deployment()
            client.deployment.update.side_effect = no_op_error
            result = CliRunner().invoke(
                cli,
                [
                    "endpoint",
                    "update",
                    "-n",
                    "test-endpoint",
                    "--header-based-routing",
                    "false",
                ],
            )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("No changes applied", result.output)

    def test_other_client_error_propagates(self):
        # A non-"no valid field" error must NOT be swallowed as a benign no-op;
        # it bubbles up to the top-level RuntimeError handler in cli.py.
        other_error = ClientError(_FakeResponse(400, '{"message":"boom"}'))
        with patch("leptonai.cli.deployment.APIClient") as MockClient:
            client = MockClient.return_value
            client.deployment.get.return_value = _make_existing_deployment()
            client.deployment.update.side_effect = other_error
            result = CliRunner().invoke(
                cli,
                [
                    "endpoint",
                    "update",
                    "-n",
                    "test-endpoint",
                    "--header-based-routing",
                    "false",
                ],
            )
        self.assertNotEqual(result.exit_code, 0)
        self.assertNotIn("No changes applied", result.output)
        self.assertIn("boom", result.output)

    def test_update_passes_routing_value_to_spec(self):
        # "TRUE" is accepted case-insensitively by click.BOOL and reaches the spec.
        with patch("leptonai.cli.deployment.APIClient") as MockClient:
            client = MockClient.return_value
            client.deployment.get.return_value = _make_existing_deployment()
            client.deployment.update.return_value = _make_existing_deployment()
            result = CliRunner().invoke(
                cli,
                [
                    "endpoint",
                    "update",
                    "-n",
                    "test-endpoint",
                    "--header-based-routing",
                    "TRUE",
                ],
            )
        self.assertEqual(result.exit_code, 0, result.output)
        sent_spec = client.deployment.update.call_args.kwargs["spec"]
        self.assertTrue(
            sent_spec.spec.routing_policy.enable_header_based_replica_routing
        )


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# `lep endpoint list` filters (pytest style)
# ---------------------------------------------------------------------------


def _endpoint(
    name,
    *,
    state="Ready",
    phase=None,
    created_by=None,
    owner=None,
    node_groups=None,
    is_pod=False,
):
    affinity = (
        LeptonResourceAffinity(allowed_dedicated_node_groups=list(node_groups))
        if node_groups
        else None
    )
    return LeptonDeployment(
        metadata=Metadata(
            id=f"{name}-id",
            name=name,
            created_at=1000,
            created_by=created_by,
            owner=owner or created_by,
        ),
        spec=LeptonDeploymentUserSpec(
            is_pod=is_pod,
            resource_requirement=ResourceRequirement(
                resource_shape="cpu.small", min_replicas=1, affinity=affinity
            ),
        ),
        status=LeptonDeploymentStatus(
            state=state,
            phase=phase,
            endpoint={"internal_endpoint": "", "external_endpoint": ""},
        ),
    )


@pytest.fixture
def endpoints():
    return [
        _endpoint(
            "Alpha-API",
            state="Ready",
            created_by="alice@example.com",
            node_groups=["h100-cluster"],
        ),
        _endpoint(
            "beta-worker",
            state="Not Ready",
            phase="Stopped",
            created_by="bob@example.com",
            node_groups=["a100-cluster"],
        ),
        _endpoint("gamma-api", state="Starting", created_by="alice@example.com"),
    ]


def _endpoint_names(items):
    return [item.metadata.name for item in items]


@pytest.mark.parametrize(
    "keyword, expected",
    [
        ("api", ["Alpha-API", "gamma-api"]),
        ("ALPHA", ["Alpha-API"]),
        ("worker-id", ["beta-worker"]),
        ("nomatch", []),
    ],
)
def test_filter_endpoints_keyword_matches_name_or_id_case_insensitively(
    endpoints, keyword, expected
):
    assert _endpoint_names(_filter_endpoints(endpoints, keyword=keyword)) == expected


def test_filter_endpoints_state_matches_displayed_state_or_phase(endpoints):
    assert _endpoint_names(_filter_endpoints(endpoints, states=["Not Ready"])) == [
        "beta-worker"
    ]
    assert _endpoint_names(_filter_endpoints(endpoints, states=["Stopped"])) == [
        "beta-worker"
    ]
    assert _endpoint_names(
        _filter_endpoints(endpoints, states=["Ready", "Starting"])
    ) == ["Alpha-API", "gamma-api"]
    assert _filter_endpoints(endpoints, states=["Error"]) == []


def test_filter_endpoints_creator_is_case_insensitive_prefix(endpoints):
    assert _endpoint_names(_filter_endpoints(endpoints, creators=["ALICE"])) == [
        "Alpha-API",
        "gamma-api",
    ]
    assert _endpoint_names(
        _filter_endpoints(endpoints, creators=["bob@example.com"])
    ) == ["beta-worker"]
    assert _filter_endpoints(endpoints, creators=["example.com"]) == []


def test_filter_endpoints_node_group_is_case_insensitive_substring(endpoints):
    assert _endpoint_names(_filter_endpoints(endpoints, node_groups=["H100"])) == [
        "Alpha-API"
    ]
    assert _endpoint_names(
        _filter_endpoints(endpoints, node_groups=["h100", "a100"])
    ) == ["Alpha-API", "beta-worker"]


def test_filter_endpoints_combines_filters_with_and(endpoints):
    assert _endpoint_names(
        _filter_endpoints(
            endpoints, names=["api"], creators=["alice"], states=["Ready"]
        )
    ) == ["Alpha-API"]
    assert _filter_endpoints(endpoints, names=["api"], states=["Not Ready"]) == []


def _invoke_endpoint_list(items, args):
    fake_client = SimpleNamespace(
        deployment=SimpleNamespace(list_all=lambda: items),
        get_dashboard_base_url=lambda: None,
    )
    with patch("leptonai.cli.deployment.APIClient", return_value=fake_client):
        return CliRunner().invoke(cli, ["endpoint", "list", *args])


def test_endpoint_list_applies_filters_and_ignores_pods(endpoints, monkeypatch):
    monkeypatch.setattr(deployment_console, "width", 240)
    items = endpoints + [
        _endpoint("alice-pod", created_by="alice@example.com", is_pod=True)
    ]
    result = _invoke_endpoint_list(
        items, ["-u", "alice", "-s", "ready", "-s", "starting"]
    )
    assert result.exit_code == 0, result.output
    assert "Alpha-API" in result.output
    assert "gamma-api" in result.output
    assert "beta-worker" not in result.output
    assert "alice-pod" not in result.output


@pytest.mark.parametrize(
    "spelling", ["Not Ready", "not ready", "NotReady", "not-ready"]
)
def test_endpoint_list_accepts_loose_state_spellings(endpoints, monkeypatch, spelling):
    monkeypatch.setattr(deployment_console, "width", 240)
    result = _invoke_endpoint_list(endpoints, ["--state", spelling])
    assert result.exit_code == 0, result.output
    assert "beta-worker" in result.output
    assert "Alpha-API" not in result.output


def test_endpoint_list_reports_when_no_endpoint_matches(endpoints):
    result = _invoke_endpoint_list(endpoints, ["--search", "nothing-here"])
    assert result.exit_code == 0, result.output
    assert "No endpoints match the specified filters." in result.output


def test_endpoint_list_keeps_empty_workspace_message_without_filters():
    result = _invoke_endpoint_list([], [])
    assert result.exit_code == 0, result.output
    assert "No endpoints found." in result.output


def test_endpoint_list_rejects_unknown_state(endpoints):
    result = _invoke_endpoint_list(endpoints, ["--state", "bogus"])
    assert result.exit_code == 2
    assert "Invalid value for '--state'" in result.output
    assert "'Not Ready'" in result.output
