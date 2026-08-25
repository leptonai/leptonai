"""Acceptance tests for LEP-6218 secure endpoint authentication CLI UX."""

import io
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

# Never consult a developer's real workspace record while constructing clients.
os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

from click.testing import CliRunner
from loguru import logger

from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.deployment import (
    LeptonContainer,
    LeptonDeployment,
    LeptonDeploymentStatus,
    LeptonDeploymentUserSpec,
    ResourceRequirement,
    TokenVar,
)
from leptonai.api.v2.types.workspace import WorkspaceFeatures
from leptonai.cli import lep

_COMMAND_GROUPS = ("endpoint", "deployment")
_GENERATED_TOKEN = "lep6218-generated-token"
_TOKEN_LABEL = "Generated API Token (save this value):"
_UNSET = object()


def _deployment(
    *,
    name="ep",
    api_tokens=_UNSET,
    allow_unauthenticated_access=_UNSET,
    ip_allowlist=_UNSET,
    image="nginx",
):
    spec_fields = {
        "container": LeptonContainer(image=image),
        "resource_requirement": ResourceRequirement(resource_shape="cpu.small"),
    }
    if api_tokens is not _UNSET:
        spec_fields["api_tokens"] = api_tokens
    if allow_unauthenticated_access is not _UNSET:
        spec_fields["allow_unauthenticated_access"] = allow_unauthenticated_access
    if ip_allowlist is not _UNSET:
        spec_fields["auth_config"] = {"ip_allowlist": ip_allowlist}
    return LeptonDeployment(
        metadata=Metadata(id=name, name=name, created_at=1000),
        spec=LeptonDeploymentUserSpec(**spec_fields),
        status=LeptonDeploymentStatus(
            state="Ready",
            endpoint={"internal_endpoint": "", "external_endpoint": ""},
        ),
    )


def _fake_client(
    *,
    secure_defaults=True,
    created=None,
    existing=None,
    info_error=None,
):
    deployment_api = Mock()
    deployment_api.list_all.return_value = []
    deployment_api.validate_create.return_value = None
    deployment_api.create.return_value = True
    deployment_api.create_with_response.return_value = created or _deployment()
    deployment_api.get.return_value = existing or _deployment()
    deployment_api.update.return_value = existing or _deployment()
    deployment_api.get_readiness.return_value = SimpleNamespace(root={})
    deployment_api.get_termination.return_value = SimpleNamespace(root={})

    client = SimpleNamespace(deployment=deployment_api)
    if info_error is not None:
        client.info = Mock(side_effect=info_error)
    else:
        features = (
            WorkspaceFeatures()
            if secure_defaults is _UNSET
            else WorkspaceFeatures(
                enable_secure_endpoint_defaults=secure_defaults,
            )
        )
        client.info = Mock(return_value=SimpleNamespace(features=features))
    return client


def _create_args(group, *extra):
    return [
        group,
        "create",
        "--name",
        "ep",
        "--container-image",
        "nginx",
        "--resource-shape",
        "cpu.small",
        "--no-traffic-timeout",
        "0",
        *extra,
    ]


def _invoke(args, client):
    with patch("leptonai.cli.deployment.APIClient", return_value=client):
        return CliRunner().invoke(lep, args)


def _created_spec(client):
    call = client.deployment.create_with_response.call_args
    if call is None:
        call = client.deployment.create.call_args
    return call.args[0].spec


def _assert_not_created(client):
    client.deployment.create.assert_not_called()
    client.deployment.create_with_response.assert_not_called()


def _updated_spec(client):
    return client.deployment.update.call_args.kwargs["spec"].spec


class TestSecureEndpointCreateCLI(unittest.TestCase):
    # LEP-6218: feature-enabled default creation defers token generation to the
    # server, suppresses the legacy unauthenticated warning, and presents the
    # returned literal exactly once in the designated user-output channel.
    def test_default_create_prints_generated_token_without_logging_it(self):
        for group in _COMMAND_GROUPS:
            with self.subTest(group=group):
                client = _fake_client(
                    secure_defaults=True,
                    created=_deployment(
                        api_tokens=[TokenVar(value=_GENERATED_TOKEN)],
                        allow_unauthenticated_access=False,
                    ),
                )
                captured_logs = io.StringIO()
                sink_id = logger.add(
                    captured_logs,
                    format="{message}",
                    level="TRACE",
                )
                try:
                    result = _invoke(_create_args(group), client)
                finally:
                    logger.remove(sink_id)

                self.assertEqual(result.exit_code, 0, result.output)
                sent = _created_spec(client)
                self.assertIsNone(sent.api_tokens)
                self.assertIsNone(sent.allow_unauthenticated_access)
                self.assertIn(f"{_TOKEN_LABEL}\n{_GENERATED_TOKEN}", result.output)
                self.assertEqual(result.output.count(_GENERATED_TOKEN), 1)
                self.assertNotIn("publicly accessible endpoint", result.output)
                self.assertNotIn("disables API-token authentication", result.output)
                self.assertNotIn(_GENERATED_TOKEN, result.stderr)
                self.assertNotIn(_GENERATED_TOKEN, captured_logs.getvalue())
                self.assertIsNone(result.exception)
                client.deployment.create.assert_not_called()
                client.deployment.create_with_response.assert_called_once()
                self.assertIs(
                    client.deployment.create_with_response.call_args.kwargs[
                        "tolerate_legacy_response"
                    ],
                    False,
                )

    # LEP-6218: disabled or absent workspace feature information retains the
    # legacy empty-token payload and warning.
    def test_default_create_uses_legacy_fallback_when_feature_is_not_enabled(self):
        fallback_cases = {
            "disabled": {"secure_defaults": False},
            "missing": {"secure_defaults": _UNSET},
        }
        for group in _COMMAND_GROUPS:
            for case, client_args in fallback_cases.items():
                with self.subTest(group=group, case=case):
                    client = _fake_client(
                        **client_args,
                        created=_deployment(api_tokens=[]),
                    )
                    result = _invoke(_create_args(group), client)

                    self.assertEqual(result.exit_code, 0, result.output)
                    sent = _created_spec(client)
                    self.assertEqual(sent.api_tokens, [])
                    self.assertIsNone(sent.allow_unauthenticated_access)
                    self.assertIn("publicly accessible endpoint", result.output)
                    self.assertNotIn(_TOKEN_LABEL, result.output)
                    client.deployment.create.assert_not_called()
                    client.deployment.create_with_response.assert_called_once()
                    self.assertIs(
                        client.deployment.create_with_response.call_args.kwargs[
                            "tolerate_legacy_response"
                        ],
                        True,
                    )

    # LEP-6218 rollout race: a legacy discovery result remains tolerant of old
    # responses, but surfaces a literal token if the server has already rolled
    # forward and generates one.
    def test_legacy_discovery_still_surfaces_server_generated_token(self):
        race_token = "lep6218-rollout-race-token"
        for group in _COMMAND_GROUPS:
            with self.subTest(group=group):
                client = _fake_client(
                    secure_defaults=False,
                    created=_deployment(
                        api_tokens=[TokenVar(value=race_token)],
                        allow_unauthenticated_access=False,
                    ),
                )

                result = _invoke(_create_args(group), client)

                self.assertEqual(result.exit_code, 0, result.output)
                self.assertIn(f"{_TOKEN_LABEL}\n{race_token}", result.output)
                self.assertEqual(result.output.count(race_token), 1)
                sent = _created_spec(client)
                self.assertEqual(sent.api_tokens, [])
                client.deployment.create.assert_not_called()
                self.assertIs(
                    client.deployment.create_with_response.call_args.kwargs[
                        "tolerate_legacy_response"
                    ],
                    True,
                )

    # LEP-6218 security: secure discovery promises a generated credential. A
    # full response without one reports post-create remediation and must not
    # print the normal success message.
    def test_secure_default_without_returned_token_reports_recovery_error(self):
        for group in _COMMAND_GROUPS:
            with self.subTest(group=group):
                client = _fake_client(
                    secure_defaults=True,
                    created=_deployment(
                        api_tokens=[],
                        allow_unauthenticated_access=False,
                    ),
                )

                result = _invoke(_create_args(group), client)

                self.assertNotEqual(result.exit_code, 0)
                normalized_output = " ".join(result.output.split())
                self.assertIn(
                    "The endpoint was created, but the server did not return a "
                    "generated API token",
                    normalized_output,
                )
                self.assertIn(
                    "lep endpoint update -n ep --tokens TOKEN",
                    normalized_output,
                )
                self.assertNotIn("Created Successfully", result.output)
                self.assertNotIn(_TOKEN_LABEL, result.output)
                client.deployment.create.assert_not_called()
                self.assertIs(
                    client.deployment.create_with_response.call_args.kwargs[
                        "tolerate_legacy_response"
                    ],
                    False,
                )

    # LEP-6218 security: if workspace feature discovery fails, creation stops
    # before mutation and reports only the generic secure-default failure.
    def test_workspace_info_failure_aborts_create_without_leaking_details(self):
        failure_secret = "lep6218-workspace-info-failure-secret"
        for group in _COMMAND_GROUPS:
            with self.subTest(group=group):
                client = _fake_client(
                    info_error=RuntimeError(failure_secret),
                )

                result = _invoke(_create_args(group), client)

                self.assertNotEqual(result.exit_code, 0)
                normalized_output = " ".join(result.output.split())
                self.assertIn(
                    "Could not determine the workspace's secure endpoint default. "
                    "No endpoint was created",
                    normalized_output,
                )
                self.assertNotIn(failure_secret, result.output)
                self.assertNotIn(failure_secret, result.stderr)
                self.assertNotIn(failure_secret, str(result.exception))
                _assert_not_created(client)

    # LEP-6218: explicit CLI authentication is decisive, so it neither depends
    # on workspace feature discovery nor exposes a discovery failure.
    def test_explicit_auth_modes_proceed_when_workspace_info_is_unavailable(self):
        failure_secret = "lep6218-unused-workspace-info-secret"
        cases = (
            (
                "tokens",
                ["--tokens", "caller-token"],
                ["caller-token"],
                None,
            ),
            (
                "opt-out",
                ["--allow-unauthenticated-access"],
                [],
                True,
            ),
        )
        for group in _COMMAND_GROUPS:
            for case, args, expected_tokens, expected_allow in cases:
                with self.subTest(group=group, case=case):
                    client = _fake_client(
                        info_error=RuntimeError(failure_secret),
                    )

                    result = _invoke(_create_args(group, *args), client)

                    self.assertEqual(result.exit_code, 0, result.output)
                    sent = _created_spec(client)
                    self.assertEqual(
                        [token.value for token in sent.api_tokens],
                        expected_tokens,
                    )
                    self.assertIs(
                        sent.allow_unauthenticated_access,
                        expected_allow,
                    )
                    self.assertNotIn(failure_secret, result.output)
                    self.assertNotIn(failure_secret, result.stderr)
                    client.info.assert_not_called()
                    client.deployment.create.assert_called_once()
                    client.deployment.create_with_response.assert_not_called()

    # LEP-6218: repeatable --tokens preserves every caller value and selects
    # protected mode without presenting those caller-known values as generated.
    def test_supplied_tokens_are_preserved_without_generated_token_output(self):
        caller_tokens = ["caller-token-a", "caller-token-b"]
        for group in _COMMAND_GROUPS:
            for feature_case, secure_defaults in (
                ("enabled", True),
                ("disabled", False),
                ("absent", _UNSET),
            ):
                with self.subTest(group=group, feature_case=feature_case):
                    client = _fake_client(
                        secure_defaults=secure_defaults,
                        created=_deployment(
                            api_tokens=[
                                TokenVar(value=value) for value in caller_tokens
                            ],
                        ),
                    )
                    result = _invoke(
                        _create_args(
                            group,
                            "--tokens",
                            caller_tokens[0],
                            "--tokens",
                            caller_tokens[1],
                        ),
                        client,
                    )

                    self.assertEqual(result.exit_code, 0, result.output)
                    sent = _created_spec(client)
                    self.assertEqual(
                        [token.value for token in sent.api_tokens],
                        caller_tokens,
                    )
                    self.assertIsNone(sent.allow_unauthenticated_access)
                    self.assertNotIn(_TOKEN_LABEL, result.output)
                    for token in caller_tokens:
                        self.assertNotIn(token, result.output)
                    client.deployment.create.assert_called_once()
                    client.deployment.create_with_response.assert_not_called()

    # LEP-6218: explicit opt-out is an atomic true + empty-list payload and is
    # accompanied by an unambiguous warning.
    def test_explicit_opt_out_sends_atomic_payload_and_warns(self):
        for group in _COMMAND_GROUPS:
            with self.subTest(group=group):
                client = _fake_client(
                    created=_deployment(
                        api_tokens=[],
                        allow_unauthenticated_access=True,
                    )
                )
                result = _invoke(
                    _create_args(group, "--allow-unauthenticated-access"),
                    client,
                )

                self.assertEqual(result.exit_code, 0, result.output)
                sent = _created_spec(client)
                self.assertIs(sent.allow_unauthenticated_access, True)
                self.assertEqual(sent.api_tokens, [])
                self.assertIn("disables API-token authentication", result.output)
                self.assertNotIn(_TOKEN_LABEL, result.output)

    # LEP-6218: the two explicit authentication modes are mutually exclusive.
    def test_tokens_and_explicit_opt_out_conflict_without_creating(self):
        for group in _COMMAND_GROUPS:
            with self.subTest(group=group):
                client = _fake_client()
                result = _invoke(
                    _create_args(
                        group,
                        "--tokens",
                        "caller-token",
                        "--allow-unauthenticated-access",
                    ),
                    client,
                )

                self.assertNotEqual(result.exit_code, 0)
                self.assertIn("Cannot specify both", result.output)
                _assert_not_created(client)

    # LEP-6218: --public controls only the IP allowlist and still follows the
    # secure workspace's token-generation default.
    def test_public_only_changes_network_access(self):
        for group in _COMMAND_GROUPS:
            with self.subTest(group=group):
                client = _fake_client(
                    created=_deployment(
                        api_tokens=[TokenVar(value=_GENERATED_TOKEN)],
                        allow_unauthenticated_access=False,
                    )
                )
                result = _invoke(_create_args(group, "--public"), client)

                self.assertEqual(result.exit_code, 0, result.output)
                sent = _created_spec(client)
                self.assertEqual(sent.auth_config.ip_allowlist, [])
                self.assertIsNone(sent.api_tokens)
                self.assertIsNone(sent.allow_unauthenticated_access)
                self.assertIn(f"{_TOKEN_LABEL}\n{_GENERATED_TOKEN}", result.output)
                self.assertNotIn("publicly accessible endpoint", result.output)

    # LEP-6218: file-only auth state is retained, while an explicit CLI auth
    # mode replaces file auth state atomically.
    def test_file_auth_round_trip_and_cli_override_precedence(self):
        cases = (
            (
                "file opt-out",
                {
                    "allow_unauthenticated_access": True,
                    "api_tokens": [],
                },
                [],
                True,
                [],
            ),
            (
                "cli tokens override file opt-out",
                {
                    "allow_unauthenticated_access": True,
                    "api_tokens": [],
                },
                ["--tokens", "replacement-token"],
                None,
                ["replacement-token"],
            ),
            (
                "cli opt-out overrides file tokens",
                {
                    "allow_unauthenticated_access": False,
                    "api_tokens": [{"value": "file-token"}],
                },
                ["--allow-unauthenticated-access"],
                True,
                [],
            ),
        )
        for group in _COMMAND_GROUPS:
            for case, auth_fields, cli_args, expected_allow, expected_tokens in cases:
                with self.subTest(group=group, case=case):
                    spec_data = {
                        "container": {"image": "nginx"},
                        "resource_requirement": {"resource_shape": "cpu.small"},
                        **auth_fields,
                    }
                    client = _fake_client(
                        created=_deployment(
                            api_tokens=[
                                TokenVar(value=value) for value in expected_tokens
                            ],
                            allow_unauthenticated_access=expected_allow,
                        )
                    )
                    runner = CliRunner()
                    with runner.isolated_filesystem():
                        with open("endpoint.json", "w") as spec_file:
                            json.dump(spec_data, spec_file)
                        with patch(
                            "leptonai.cli.deployment.APIClient",
                            return_value=client,
                        ):
                            result = runner.invoke(
                                lep,
                                [
                                    group,
                                    "create",
                                    "--name",
                                    "ep",
                                    "--file",
                                    "endpoint.json",
                                    "--no-traffic-timeout",
                                    "0",
                                    *cli_args,
                                ],
                            )

                    self.assertEqual(result.exit_code, 0, result.output)
                    sent = _created_spec(client)
                    self.assertIs(
                        sent.allow_unauthenticated_access,
                        expected_allow,
                    )
                    self.assertEqual(
                        [token.value for token in sent.api_tokens],
                        expected_tokens,
                    )

    # LEP-6218: an invalid file that selects both auth modes is rejected rather
    # than silently selecting one.
    def test_file_only_tokens_and_opt_out_combination_is_rejected(self):
        for group in _COMMAND_GROUPS:
            with self.subTest(group=group):
                spec_data = {
                    "container": {"image": "nginx"},
                    "resource_requirement": {"resource_shape": "cpu.small"},
                    "allow_unauthenticated_access": True,
                    "api_tokens": [{"value": "file-token"}],
                }
                client = _fake_client()
                runner = CliRunner()
                with runner.isolated_filesystem():
                    with open("endpoint.json", "w") as spec_file:
                        json.dump(spec_data, spec_file)
                    with patch(
                        "leptonai.cli.deployment.APIClient",
                        return_value=client,
                    ):
                        result = runner.invoke(
                            lep,
                            [
                                group,
                                "create",
                                "--name",
                                "ep",
                                "--file",
                                "endpoint.json",
                                "--no-traffic-timeout",
                                "0",
                            ],
                        )

                self.assertNotEqual(result.exit_code, 0)
                self.assertIn("cannot combine", result.output.lower())
                _assert_not_created(client)

    # LEP-6218 scope guard: endpoint unauthenticated-access controls cannot be
    # applied to pod-flavoured files, even when a false value is present.
    def test_pod_file_rejects_endpoint_only_opt_out_before_api_access(self):
        cases = (
            ("file true", True, []),
            ("file false", False, []),
            ("CLI opt-out", _UNSET, ["--allow-unauthenticated-access"]),
        )
        for group in _COMMAND_GROUPS:
            for case, file_allow, cli_args in cases:
                with self.subTest(group=group, case=case):
                    spec_data = {
                        "is_pod": True,
                        "container": {"image": "ubuntu"},
                        "resource_requirement": {
                            "resource_shape": "cpu.small",
                        },
                    }
                    if file_allow is not _UNSET:
                        spec_data["allow_unauthenticated_access"] = file_allow
                    client = _fake_client()
                    client.pod = Mock()
                    runner = CliRunner()
                    with runner.isolated_filesystem():
                        with open("pod.json", "w") as spec_file:
                            json.dump(spec_data, spec_file)
                        with patch(
                            "leptonai.cli.deployment.APIClient",
                            return_value=client,
                        ):
                            result = runner.invoke(
                                lep,
                                [
                                    group,
                                    "create",
                                    "--name",
                                    "pod",
                                    "--file",
                                    "pod.json",
                                    *cli_args,
                                ],
                            )

                    self.assertNotEqual(result.exit_code, 0)
                    self.assertIn(
                        "applies only to endpoints",
                        result.output.lower(),
                    )
                    self.assertNotIn(
                        "disables API-token authentication",
                        result.output,
                    )
                    self.assertEqual(client.deployment.mock_calls, [])
                    self.assertEqual(client.pod.mock_calls, [])
                    client.info.assert_not_called()


class TestSecureEndpointUpdateCLI(unittest.TestCase):
    # LEP-6218: unrelated updates are sparse for both protected and explicitly
    # unauthenticated endpoints, preserving server-side authentication state.
    def test_unrelated_update_omits_both_authentication_fields(self):
        existing_modes = (
            _deployment(
                api_tokens=[TokenVar(value="existing-token")],
                allow_unauthenticated_access=False,
            ),
            _deployment(api_tokens=[], allow_unauthenticated_access=True),
        )
        for group in _COMMAND_GROUPS:
            for existing in existing_modes:
                with self.subTest(
                    group=group,
                    existing_allow=existing.spec.allow_unauthenticated_access,
                ):
                    client = _fake_client(existing=existing)
                    result = _invoke(
                        [
                            group,
                            "update",
                            "--name",
                            "ep",
                            "--container-image",
                            "nginx:new",
                        ],
                        client,
                    )

                    self.assertEqual(result.exit_code, 0, result.output)
                    sent = _updated_spec(client)
                    self.assertIsNone(sent.api_tokens)
                    self.assertIsNone(sent.allow_unauthenticated_access)

    # LEP-6218: authentication mode transitions are represented as one atomic
    # update payload rather than a token-clear followed by a mode change.
    def test_authentication_transitions_are_atomic(self):
        cases = (
            (
                "protected to unauthenticated",
                _deployment(
                    api_tokens=[TokenVar(value="old-token")],
                    allow_unauthenticated_access=False,
                ),
                ["--allow-unauthenticated-access"],
                True,
                [],
            ),
            (
                "unauthenticated to protected",
                _deployment(api_tokens=[], allow_unauthenticated_access=True),
                ["--tokens", "new-token"],
                False,
                ["new-token"],
            ),
            (
                "replace protected tokens",
                _deployment(
                    api_tokens=[TokenVar(value="old-token")],
                    allow_unauthenticated_access=False,
                ),
                ["--tokens", "new-a", "--tokens", "new-b"],
                False,
                ["new-a", "new-b"],
            ),
        )
        for group in _COMMAND_GROUPS:
            for case, existing, args, expected_allow, expected_tokens in cases:
                with self.subTest(group=group, case=case):
                    client = _fake_client(existing=existing)
                    result = _invoke(
                        [group, "update", "--name", "ep", *args],
                        client,
                    )

                    self.assertEqual(result.exit_code, 0, result.output)
                    sent = _updated_spec(client)
                    self.assertIs(
                        sent.allow_unauthenticated_access,
                        expected_allow,
                    )
                    self.assertEqual(
                        [token.value for token in sent.api_tokens],
                        expected_tokens,
                    )
                    if expected_allow:
                        self.assertIn(
                            "disables API-token authentication",
                            result.output,
                        )

    # LEP-6218: --public is independent from token authentication on update.
    def test_public_update_omits_authentication_fields(self):
        for group in _COMMAND_GROUPS:
            with self.subTest(group=group):
                existing = _deployment(
                    api_tokens=[TokenVar(value="existing-token")],
                    allow_unauthenticated_access=False,
                )
                client = _fake_client(existing=existing)
                result = _invoke(
                    [group, "update", "--name", "ep", "--public"],
                    client,
                )

                self.assertEqual(result.exit_code, 0, result.output)
                sent = _updated_spec(client)
                self.assertEqual(sent.auth_config.ip_allowlist, [])
                self.assertIsNone(sent.api_tokens)
                self.assertIsNone(sent.allow_unauthenticated_access)

    # LEP-6218: conflicting update flags fail without mutation, and the legacy
    # token-clear escape hatch directs users through the explicit opt-out.
    def test_conflict_and_hidden_remove_tokens_path_are_rejected(self):
        cases = (
            (
                "conflicting modes",
                ["--tokens", "new-token", "--allow-unauthenticated-access"],
                "Cannot specify both",
            ),
            (
                "hidden remove path",
                ["--remove-tokens"],
                "Use --allow-unauthenticated-access",
            ),
        )
        for group in _COMMAND_GROUPS:
            for case, args, expected_message in cases:
                with self.subTest(group=group, case=case):
                    client = _fake_client(
                        existing=_deployment(
                            api_tokens=[TokenVar(value="existing-token")],
                            allow_unauthenticated_access=False,
                        )
                    )
                    result = _invoke(
                        [group, "update", "--name", "ep", *args],
                        client,
                    )

                    self.assertNotEqual(result.exit_code, 0)
                    self.assertIn(expected_message, result.output)
                    client.deployment.update.assert_not_called()

    # LEP-6218 security: trace serialization redacts both caller-supplied
    # request tokens and literal tokens returned by an update response.
    def test_update_request_and_response_tokens_are_absent_from_trace_logs(self):
        supplied_token = "lep6218-supplied-update-token"
        returned_token = "lep6218-returned-update-token"
        for group in _COMMAND_GROUPS:
            with self.subTest(group=group):
                existing = _deployment(
                    api_tokens=[TokenVar(value="old-token")],
                    allow_unauthenticated_access=False,
                )
                client = _fake_client(existing=existing)
                client.deployment.update.return_value = _deployment(
                    api_tokens=[TokenVar(value=returned_token)],
                    allow_unauthenticated_access=False,
                )
                captured_logs = io.StringIO()
                sink_id = logger.add(
                    captured_logs,
                    format="{level}:{message}",
                    level="TRACE",
                )
                try:
                    result = _invoke(
                        [
                            group,
                            "update",
                            "--name",
                            "ep",
                            "--tokens",
                            supplied_token,
                        ],
                        client,
                    )
                finally:
                    logger.remove(sink_id)

                self.assertEqual(result.exit_code, 0, result.output)
                self.assertNotIn(supplied_token, captured_logs.getvalue())
                self.assertNotIn(returned_token, captured_logs.getvalue())
                self.assertNotIn(supplied_token, result.output)
                self.assertNotIn(returned_token, result.output)


class TestSecureEndpointStatusCLI(unittest.TestCase):
    # LEP-6218: network reachability and API-token authentication are reported
    # independently for both the visible endpoint and compatibility aliases.
    def test_status_reports_network_and_token_authentication_independently(self):
        cases = (
            (
                "public protected",
                _deployment(
                    api_tokens=[TokenVar(value="protected-token")],
                    allow_unauthenticated_access=False,
                    ip_allowlist=[],
                ),
                "Yes",
                "Enabled",
            ),
            (
                "restricted opt-out",
                _deployment(
                    api_tokens=[],
                    allow_unauthenticated_access=True,
                    ip_allowlist=["192.0.2.0/24"],
                ),
                "No",
                "Disabled",
            ),
        )
        for group in _COMMAND_GROUPS:
            for case, existing, expected_public, expected_auth in cases:
                with self.subTest(group=group, case=case):
                    client = _fake_client(existing=existing)

                    result = _invoke(
                        [group, "status", "--name", "ep"],
                        client,
                    )

                    self.assertEqual(result.exit_code, 0, result.output)
                    normalized_output = " ".join(result.output.split())
                    self.assertIn(
                        f"Is Public: {expected_public}",
                        normalized_output,
                    )
                    self.assertIn(
                        f"API Token Authentication: {expected_auth}",
                        normalized_output,
                    )

    # LEP-6218 security: status detail hides response token literals by default
    # and reveals them only after an explicit --show-tokens request.
    def test_status_detail_requires_explicit_opt_in_to_show_tokens(self):
        token = "lep6218-status-detail-token"
        for group in _COMMAND_GROUPS:
            for show_tokens in (False, True):
                with self.subTest(group=group, show_tokens=show_tokens):
                    client = _fake_client(
                        existing=_deployment(
                            api_tokens=[TokenVar(value=token)],
                            allow_unauthenticated_access=False,
                            ip_allowlist=[],
                        )
                    )
                    args = [group, "status", "--name", "ep", "--detail"]
                    if show_tokens:
                        args.append("--show-tokens")

                    result = _invoke(args, client)

                    self.assertEqual(result.exit_code, 0, result.output)
                    if show_tokens:
                        self.assertIn(token, result.output)
                    else:
                        self.assertNotIn(token, result.output)


class TestSecureEndpointAuthHelp(unittest.TestCase):
    # LEP-6218: visible and compatibility command groups advertise the same
    # explicit opt-out, while the unsafe legacy removal option remains hidden.
    def test_help_documents_explicit_opt_out_and_public_independence(self):
        for group in _COMMAND_GROUPS:
            for operation in ("create", "update"):
                with self.subTest(group=group, operation=operation):
                    result = CliRunner().invoke(lep, [group, operation, "--help"])
                    self.assertEqual(result.exit_code, 0, result.output)
                    self.assertIn("--allow-unauthenticated-access", result.output)
                    self.assertIn("API-token authentication", result.output)
                    self.assertNotIn("--remove-tokens", result.output)


if __name__ == "__main__":
    unittest.main()
