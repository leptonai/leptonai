"""Public HTTP/SDK contract tests for LEP-6218 endpoint authentication."""

import json
import os
import tempfile
import unittest
import warnings
from contextlib import redirect_stderr
from io import StringIO

# Tests must never read a developer's real workspace configuration.
os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

import responses
from requests import Response

from leptonai.api.v2 import client as client_module
from leptonai.api.v2.api_resource import APIResourse, ClientError, ServerError
from leptonai.api.v2.client import APIClient
from leptonai.api.v2.endpoint import EndpointAPI
from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.deployment import (
    LeptonContainer,
    LeptonDeployment,
    LeptonDeploymentUserSpec,
    ResourceRequirement,
    TokenVar,
)

BASE = "https://gw.example/api/v2/workspaces/ws1"
_SECRET = "lep6218-contract-secret"
_ESCAPED_SECRET = 'q"\\\n\t\u2603\u00e9-secret'
_LONG_SECRET = (
    "lep6218-long-secret-prefix-" + ("x" * 192) + "-lep6218-long-secret-suffix"
)
_UNSET = object()


def _workspace_info(*, new_api, secure_defaults=True):
    return {
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
        "features": {
            "enable_new_deployment_api": new_api,
            "enable_secure_endpoint_defaults": secure_defaults,
        },
    }


def _register_workspace(*, new_api, secure_defaults=True):
    responses.add(
        responses.GET,
        f"{BASE}/workspace",
        json=_workspace_info(
            new_api=new_api,
            secure_defaults=secure_defaults,
        ),
        status=200,
    )


def _client():
    client_module.reset_new_deployment_api_flag_cache()
    return APIClient(workspace_id="ws1", auth_token="tok", url=BASE)


def _token_dicts(values):
    return [{"value": value} for value in values]


def _legacy_body(
    *,
    name="ep",
    tokens=_UNSET,
    allow_unauthenticated_access=_UNSET,
    image="nginx",
):
    spec = {
        "container": {"image": image},
        "resource_requirement": {
            "resource_shape": "cpu.small",
            "min_replicas": 1,
        },
    }
    if tokens is not _UNSET:
        spec["api_tokens"] = _token_dicts(tokens)
    if allow_unauthenticated_access is not _UNSET:
        spec["allow_unauthenticated_access"] = allow_unauthenticated_access
    return {
        "metadata": {"id": name, "name": name, "created_at": 1},
        "spec": spec,
        "status": {
            "state": "Ready",
            "endpoint": {
                "internal_endpoint": "",
                "external_endpoint": "",
            },
        },
    }


def _endpoint_body(
    *,
    name="ep",
    tokens=_UNSET,
    allow_unauthenticated_access=_UNSET,
    image="nginx",
):
    spec = {
        "components": [{
            "name": "default",
            "image": image,
            "resource_shape": "cpu.small",
            "min_replicas": 1,
        }]
    }
    if tokens is not _UNSET:
        spec["api_tokens"] = _token_dicts(tokens)
    if allow_unauthenticated_access is not _UNSET:
        spec["allow_unauthenticated_access"] = allow_unauthenticated_access
    return {
        "metadata": {"id": name, "name": name, "created_at": 1},
        "spec": spec,
        "status": {"state": "Ready"},
    }


def _response_body(*, new_api, **kwargs):
    return _endpoint_body(**kwargs) if new_api else _legacy_body(**kwargs)


def _route(*, new_api, name=None):
    family = "endpoints" if new_api else "deployments"
    suffix = f"/{name}" if name else ""
    return f"{BASE}/{family}{suffix}"


def _deployment_model(
    *,
    name="ep",
    tokens=_UNSET,
    allow_unauthenticated_access=_UNSET,
    image=_UNSET,
):
    fields = {}
    if image is not _UNSET:
        fields["container"] = LeptonContainer(image=image)
        fields["resource_requirement"] = ResourceRequirement(resource_shape="cpu.small")
    if tokens is not _UNSET:
        fields["api_tokens"] = [TokenVar(value=value) for value in tokens]
    if allow_unauthenticated_access is not _UNSET:
        fields["allow_unauthenticated_access"] = allow_unauthenticated_access
    return LeptonDeployment(
        metadata=Metadata(id=name, name=name),
        spec=LeptonDeploymentUserSpec(**fields),
    )


def _pod_model(*, allow_unauthenticated_access):
    return LeptonDeployment(
        metadata=Metadata(id="pod", name="pod"),
        spec=LeptonDeploymentUserSpec(
            is_pod=True,
            container=LeptonContainer(image="ubuntu"),
            resource_requirement=ResourceRequirement(resource_shape="cpu.small"),
            allow_unauthenticated_access=allow_unauthenticated_access,
        ),
    )


def _request_json(method, url):
    call = next(
        call
        for call in responses.calls
        if call.request.method == method and call.request.url == url
    )
    body = call.request.body
    if isinstance(body, bytes):
        body = body.decode()
    return json.loads(body)


def _assert_secret_not_rendered(test_case, text, secret=_ESCAPED_SECRET):
    """Reject decoded and common escaped renderings of a credential."""
    renderings = {
        secret,
        repr(secret)[1:-1],
        ascii(secret)[1:-1],
        json.dumps(secret)[1:-1],
        json.dumps(secret, ensure_ascii=False)[1:-1],
    }
    fragments = set()
    for rendering in renderings:
        if len(rendering) > 48:
            fragments.update((rendering[:24], rendering[-24:]))
    for rendering in renderings | fragments:
        test_case.assertNotIn(rendering, text)


def _malformed_token_entry(value):
    return {
        "value": value,
        "description": "primary rotation credential",
        "metadata": {"owner": "platform-security"},
    }


class TestSecureEndpointCreateContract(unittest.TestCase):
    # LEP-6218: both API families accept the same three create modes and return
    # a full resource whose normal response exposes literal API tokens.
    @responses.activate
    def test_create_with_response_returns_token_model_for_both_api_families(self):
        modes = (
            (
                "server generated",
                {},
                [_SECRET],
                False,
            ),
            (
                "caller supplied",
                {
                    "tokens": ["caller-a", "caller-b"],
                    "allow_unauthenticated_access": False,
                },
                ["caller-a", "caller-b"],
                False,
            ),
            (
                "explicit opt-out",
                {
                    "tokens": [],
                    "allow_unauthenticated_access": True,
                },
                [],
                True,
            ),
        )
        for new_api in (False, True):
            for mode, request_fields, response_tokens, response_allow in modes:
                with self.subTest(new_api=new_api, mode=mode):
                    responses.reset()
                    _register_workspace(new_api=new_api)
                    url = _route(new_api=new_api)
                    responses.add(
                        responses.POST,
                        url,
                        json=_response_body(
                            new_api=new_api,
                            tokens=response_tokens,
                            allow_unauthenticated_access=response_allow,
                        ),
                        status=201,
                    )

                    created = _client().deployment.create_with_response(
                        _deployment_model(image="nginx", **request_fields)
                    )

                    self.assertIsInstance(created, LeptonDeployment)
                    self.assertEqual(created.metadata.name, "ep")
                    self.assertEqual(
                        [token.value for token in created.spec.api_tokens],
                        response_tokens,
                    )
                    self.assertIs(
                        created.spec.allow_unauthenticated_access,
                        response_allow,
                    )

                    sent = _request_json("POST", url)["spec"]
                    if mode == "server generated":
                        self.assertNotIn("api_tokens", sent)
                        self.assertNotIn("allow_unauthenticated_access", sent)
                    else:
                        self.assertEqual(
                            sent["api_tokens"],
                            _token_dicts(request_fields["tokens"]),
                        )
                        self.assertIs(
                            sent["allow_unauthenticated_access"],
                            request_fields["allow_unauthenticated_access"],
                        )

    # LEP-6218 compatibility: the established create() API remains a boolean
    # status operation and does not start decoding successful response bodies.
    @responses.activate
    def test_create_remains_true_for_successful_undecodable_responses(self):
        successful_bodies = ("", "not-json", "{}")
        for new_api in (False, True):
            for body in successful_bodies:
                with self.subTest(new_api=new_api, body=body):
                    responses.reset()
                    _register_workspace(new_api=new_api)
                    url = _route(new_api=new_api)
                    responses.add(
                        responses.POST,
                        url,
                        body=body,
                        status=200,
                        content_type="application/json",
                    )

                    created = _client().deployment.create(
                        _deployment_model(image="nginx")
                    )

                    self.assertIs(created, True)

    # The historical boolean API cannot return a server-generated credential.
    # Keep it compatible, but tell SDK callers which API preserves the token.
    @responses.activate
    def test_boolean_create_warns_when_server_may_generate_the_only_token(self):
        for new_api in (False, True):
            with self.subTest(new_api=new_api):
                responses.reset()
                _register_workspace(new_api=new_api)
                url = _route(new_api=new_api)
                responses.add(
                    responses.POST,
                    url,
                    json=_response_body(
                        new_api=new_api,
                        tokens=[_SECRET],
                        allow_unauthenticated_access=False,
                    ),
                    status=201,
                )

                with warnings.catch_warnings(record=True) as emitted:
                    warnings.simplefilter("always")
                    created = _client().deployment.create(
                        _deployment_model(image="nginx")
                    )

                self.assertIs(created, True)
                self.assertTrue(
                    any(
                        "create_with_response" in str(item.message) for item in emitted
                    ),
                    "generation-eligible create() must point SDK callers to "
                    "create_with_response()",
                )
                self.assertEqual(
                    [
                        call.request.url
                        for call in responses.calls
                        if call.request.method == "POST"
                    ],
                    [url],
                )

    # The boolean compatibility method cannot return a generated credential.
    # Its warning follows the request shape, not a potentially stale or absent
    # workspace feature snapshot: a server-first rollout may secure this create
    # before the client's cached feature flag catches up.
    @responses.activate
    def test_boolean_create_warns_without_a_true_secure_default_snapshot(self):
        for new_api in (False, True):
            for snapshot_state in ("stale false", "missing"):
                with self.subTest(
                    new_api=new_api,
                    snapshot_state=snapshot_state,
                ):
                    responses.reset()
                    _register_workspace(
                        new_api=new_api,
                        secure_defaults=False,
                    )
                    client = _client()
                    deployment_api = client.deployment
                    if snapshot_state == "missing":
                        client._deployment_api_workspace_info = None

                    url = _route(new_api=new_api)
                    responses.add(
                        responses.POST,
                        url,
                        json=_response_body(
                            new_api=new_api,
                            tokens=[_SECRET],
                            allow_unauthenticated_access=False,
                        ),
                        status=201,
                    )

                    with warnings.catch_warnings(record=True) as emitted:
                        warnings.simplefilter("always")
                        created = deployment_api.create(
                            _deployment_model(image="nginx")
                        )

                    self.assertIs(created, True)
                    matching_warnings = [
                        item
                        for item in emitted
                        if "create_with_response" in str(item.message)
                    ]
                    self.assertEqual(len(matching_warnings), 1)
                    self.assertIs(matching_warnings[0].category, RuntimeWarning)
                    self.assertEqual(
                        [
                            call.request.url
                            for call in responses.calls
                            if call.request.method == "POST"
                        ],
                        [url],
                    )

    # LEP-6218: GET and spec export retain explicit opt-out in both API
    # families, so the exported document can be loaded as a fresh file spec.
    @responses.activate
    def test_get_export_and_reload_preserve_explicit_opt_out(self):
        for new_api in (False, True):
            with self.subTest(new_api=new_api):
                responses.reset()
                _register_workspace(new_api=new_api)
                url = _route(new_api=new_api, name="ep")
                responses.add(
                    responses.GET,
                    url,
                    json=_response_body(
                        new_api=new_api,
                        tokens=[],
                        allow_unauthenticated_access=True,
                    ),
                    status=200,
                )

                model = _client().deployment.get("ep")
                exported = json.loads(
                    model.spec.model_dump_json(by_alias=True, exclude_none=True)
                )
                reloaded = LeptonDeploymentUserSpec(**exported)

                self.assertIs(model.spec.allow_unauthenticated_access, True)
                self.assertEqual(model.spec.api_tokens, [])
                self.assertIs(exported["allow_unauthenticated_access"], True)
                self.assertEqual(exported["api_tokens"], [])
                self.assertIs(reloaded.allow_unauthenticated_access, True)
                self.assertEqual(reloaded.api_tokens, [])

    # LEP-6218 rollout compatibility: token-free legacy 2xx bodies become the
    # historical True result only when the caller explicitly enables tolerance.
    @responses.activate
    def test_empty_legacy_success_requires_explicit_legacy_tolerance(self):
        malformed_bodies = ("", " \n", "{}")
        for new_api in (False, True):
            for body in malformed_bodies:
                for tolerate in (False, True):
                    with self.subTest(
                        new_api=new_api,
                        body=body,
                        tolerate=tolerate,
                    ):
                        responses.reset()
                        _register_workspace(new_api=new_api)
                        url = _route(new_api=new_api)
                        responses.add(
                            responses.POST,
                            url,
                            body=body,
                            status=200,
                            content_type="application/json",
                        )

                        if tolerate:
                            created = _client().deployment.create_with_response(
                                _deployment_model(image="nginx"),
                                tolerate_legacy_response=True,
                            )
                            self.assertIs(created, True)
                        else:
                            with self.assertRaises(RuntimeError) as raised:
                                _client().deployment.create_with_response(
                                    _deployment_model(image="nginx"),
                                    tolerate_legacy_response=False,
                                )

                            if body:
                                self.assertNotIn(body, str(raised.exception))
                            self.assertIsNone(raised.exception.__cause__)
                            self.assertTrue(raised.exception.__suppress_context__)

    # LEP-6218 security: tolerance is narrow. An arbitrary token-free malformed
    # body is not a recognized legacy response and remains a body-free error.
    @responses.activate
    def test_arbitrary_malformed_success_rejects_even_with_legacy_tolerance(self):
        body = "not-json"
        for new_api in (False, True):
            with self.subTest(new_api=new_api):
                responses.reset()
                _register_workspace(new_api=new_api)
                url = _route(new_api=new_api)
                responses.add(
                    responses.POST,
                    url,
                    body=body,
                    status=200,
                    content_type="application/json",
                )

                with self.assertRaises(RuntimeError) as raised:
                    _client().deployment.create_with_response(
                        _deployment_model(image="nginx"),
                        tolerate_legacy_response=True,
                    )

                self.assertNotIn(body, str(raised.exception))
                self.assertIsNone(raised.exception.__cause__)
                self.assertTrue(raised.exception.__suppress_context__)

    # LEP-6218 security: a malformed response containing a token cannot fall
    # back to True, even with legacy tolerance, because that would lose the
    # only returned copy of a generated credential.
    @responses.activate
    def test_token_bearing_malformed_success_never_uses_legacy_tolerance(self):
        for new_api in (False, True):
            for token_field in ("api_tokens", "apiTokens"):
                with self.subTest(new_api=new_api, token_field=token_field):
                    responses.reset()
                    _register_workspace(new_api=new_api)
                    url = _route(new_api=new_api)
                    responses.add(
                        responses.POST,
                        url,
                        json={
                            token_field: [{"value": _SECRET}],
                            "message": f"generated {_SECRET}",
                        },
                        status=200,
                    )

                    with self.assertRaises(RuntimeError) as raised:
                        _client().deployment.create_with_response(
                            _deployment_model(image="nginx"),
                            tolerate_legacy_response=True,
                        )

                    self.assertNotIn(_SECRET, str(raised.exception))
                    self.assertIsNone(raised.exception.__cause__)
                    self.assertTrue(raised.exception.__suppress_context__)

    # A token field anywhere outside spec.api_tokens is malformed and cannot be
    # accepted as a token-free success: Pydantic would otherwise ignore it.
    @responses.activate
    def test_nested_misplaced_token_fields_reject_success_for_both_api_families(self):
        for new_api in (False, True):
            for token_field in ("api_tokens", "apiTokens"):
                with self.subTest(new_api=new_api, token_field=token_field):
                    responses.reset()
                    _register_workspace(new_api=new_api)
                    body = _response_body(
                        new_api=new_api,
                        allow_unauthenticated_access=False,
                    )
                    body["metadata"][token_field] = [{"value": _SECRET}]
                    responses.add(
                        responses.POST,
                        _route(new_api=new_api),
                        json=body,
                        status=200,
                    )

                    with self.assertRaises(RuntimeError) as raised:
                        _client().deployment.create_with_response(
                            _deployment_model(image="nginx"),
                            tolerate_legacy_response=True,
                        )

                    self.assertNotIn(_SECRET, str(raised.exception))
                    self.assertTrue(raised.exception.__suppress_context__)

    # LEP-6218 security: non-2xx bodies containing snake_case or camelCase token
    # fields/messages are redacted before ClientError/ServerError construction.
    @responses.activate
    def test_non_success_create_errors_redact_token_material(self):
        error_cases = (
            (400, ClientError, "api_tokens"),
            (500, ServerError, "apiTokens"),
        )
        for new_api in (False, True):
            for method_name in ("create", "create_with_response"):
                for status, error_type, field_name in error_cases:
                    with self.subTest(
                        new_api=new_api,
                        method=method_name,
                        status=status,
                        field_name=field_name,
                    ):
                        responses.reset()
                        _register_workspace(new_api=new_api)
                        url = _route(new_api=new_api)
                        responses.add(
                            responses.POST,
                            url,
                            json={
                                "message": f"rejected {field_name} value {_SECRET}",
                                field_name: [{"value": _SECRET}],
                            },
                            status=status,
                        )

                        with self.assertRaises(error_type) as raised:
                            create = getattr(_client().deployment, method_name)
                            create(_deployment_model(image="nginx"))

                        self.assertNotIn(_SECRET, str(raised.exception))
                        self.assertNotIn(_SECRET, raised.exception.response.text)
                        self.assertEqual(raised.exception.response.status_code, status)

    # A client-side validation response is safe and useful once any structured
    # token values have been removed, even when the server may have generated a
    # token for the default authentication mode.
    @responses.activate
    def test_default_create_4xx_preserves_actionable_structured_diagnostic(self):
        message = "api_tokens must contain exactly one valid credential"
        for new_api in (False, True):
            for method_name in ("create", "create_with_response"):
                with self.subTest(new_api=new_api, method=method_name):
                    responses.reset()
                    _register_workspace(new_api=new_api)
                    responses.add(
                        responses.POST,
                        _route(new_api=new_api),
                        json={
                            "message": message,
                            "details": {
                                "apiTokens": [{"value": _SECRET}],
                            },
                        },
                        status=422,
                    )

                    create = getattr(_client().deployment, method_name)
                    with self.assertRaises(ClientError) as raised:
                        create(_deployment_model(image="nginx"))

                    diagnostic = raised.exception.response
                    self.assertIn(message, str(raised.exception))
                    self.assertEqual(diagnostic.json()["message"], message)
                    self.assertEqual(
                        diagnostic.json()["details"]["apiTokens"],
                        [{"value": "***"}],
                    )
                    self.assertNotIn(_SECRET, diagnostic.text)

    # A 5xx can be emitted after a generated credential exists, so default
    # creates must not retain any server response body in the exception.
    @responses.activate
    def test_default_create_5xx_uses_generic_diagnostic(self):
        unsafe_detail = "backend failed after credential generation"
        for new_api in (False, True):
            for method_name in ("create", "create_with_response"):
                with self.subTest(new_api=new_api, method=method_name):
                    responses.reset()
                    _register_workspace(new_api=new_api)
                    responses.add(
                        responses.POST,
                        _route(new_api=new_api),
                        json={
                            "message": unsafe_detail,
                            "api_tokens": [{"value": _SECRET}],
                        },
                        status=500,
                    )

                    create = getattr(_client().deployment, method_name)
                    with self.assertRaises(ServerError) as raised:
                        create(_deployment_model(image="nginx"))

                    self.assertEqual(
                        raised.exception.response.text,
                        APIResourse._REDACTED_DIAGNOSTIC,
                    )
                    self.assertNotIn(unsafe_detail, str(raised.exception))
                    self.assertNotIn(_SECRET, str(raised.exception))

    # LEP-6218 security: response-returning create cannot reliably identify a
    # markerless generated credential in a downstream 5xx, so its body is
    # generic. A 4xx is treated as pre-generation validation and remains useful.
    @responses.activate
    def test_create_with_response_redacts_markerless_downstream_5xx(self):
        for new_api in (False, True):
            with self.subTest(new_api=new_api):
                responses.reset()
                _register_workspace(new_api=new_api)
                url = _route(new_api=new_api)
                responses.add(
                    responses.POST,
                    url,
                    body=f"downstream failure {_SECRET}",
                    status=500,
                    content_type="text/plain",
                )

                with self.assertRaises(ServerError) as raised:
                    _client().deployment.create_with_response(
                        _deployment_model(image="nginx")
                    )

                self.assertNotIn(_SECRET, str(raised.exception))
                self.assertNotIn(_SECRET, raised.exception.response.text)
                self.assertEqual(raised.exception.response.status_code, 500)

    @responses.activate
    def test_explicit_token_markerless_errors_are_sanitized(self):
        for new_api in (False, True):
            for operation in ("create", "update"):
                for status, error_type in ((400, ClientError), (500, ServerError)):
                    with self.subTest(
                        new_api=new_api,
                        operation=operation,
                        status=status,
                    ):
                        responses.reset()
                        _register_workspace(new_api=new_api)
                        url = _route(
                            new_api=new_api,
                            name="ep" if operation == "update" else None,
                        )
                        if new_api and operation == "update":
                            responses.add(
                                responses.GET,
                                url,
                                json=_endpoint_body(
                                    tokens=["old-token"],
                                    allow_unauthenticated_access=False,
                                ),
                                status=200,
                            )
                        responses.add(
                            (
                                responses.POST
                                if operation == "create"
                                else responses.PATCH
                            ),
                            url,
                            body=f"invalid token {_SECRET}",
                            status=status,
                            content_type="text/plain",
                        )

                        api = _client().deployment
                        request = _deployment_model(
                            image="nginx" if operation == "create" else _UNSET,
                            tokens=[_SECRET],
                            allow_unauthenticated_access=False,
                        )
                        with self.assertRaises(error_type) as raised:
                            if operation == "create":
                                api.create(request)
                            else:
                                api.update("ep", request)

                        self.assertIn("invalid token ***", str(raised.exception))
                        self.assertNotIn(_SECRET, str(raised.exception))
                        self.assertNotIn(_SECRET, raised.exception.response.text)

    @responses.activate
    def test_valid_looking_top_level_token_response_is_rejected(self):
        for new_api in (False, True):
            with self.subTest(new_api=new_api):
                responses.reset()
                _register_workspace(new_api=new_api)
                body = _response_body(new_api=new_api)
                body["api_tokens"] = [{"value": _SECRET}]
                responses.add(
                    responses.POST,
                    _route(new_api=new_api),
                    json=body,
                    status=201,
                )

                with self.assertRaises(RuntimeError) as raised:
                    _client().deployment.create_with_response(
                        _deployment_model(image="nginx")
                    )

                self.assertNotIn(_SECRET, str(raised.exception))
                self.assertIn("response could not be decoded", str(raised.exception))

    @responses.activate
    def test_explicit_opt_out_is_normalized_to_atomic_empty_token_list(self):
        for new_api in (False, True):
            with self.subTest(new_api=new_api):
                responses.reset()
                _register_workspace(new_api=new_api)
                url = _route(new_api=new_api)
                responses.add(
                    responses.POST,
                    url,
                    json=_response_body(
                        new_api=new_api,
                        tokens=[],
                        allow_unauthenticated_access=True,
                    ),
                    status=201,
                )

                _client().deployment.create_with_response(
                    _deployment_model(
                        image="nginx",
                        allow_unauthenticated_access=True,
                    )
                )

                sent = _request_json("POST", url)["spec"]
                self.assertIs(sent["allow_unauthenticated_access"], True)
                self.assertEqual(sent["api_tokens"], [])

    @responses.activate
    def test_explicit_protected_mode_without_tokens_allows_server_default_create(self):
        for new_api in (False, True):
            for method_name in ("create", "create_with_response"):
                with self.subTest(new_api=new_api, method=method_name):
                    responses.reset()
                    _register_workspace(new_api=new_api)
                    url = _route(new_api=new_api)
                    responses.add(
                        responses.POST,
                        url,
                        json=_response_body(
                            new_api=new_api,
                            tokens=[_SECRET],
                            allow_unauthenticated_access=False,
                        ),
                        status=201,
                    )

                    create = getattr(_client().deployment, method_name)
                    created = create(
                        _deployment_model(
                            image="nginx",
                            allow_unauthenticated_access=False,
                        )
                    )

                    if method_name == "create":
                        self.assertIs(created, True)
                    else:
                        self.assertEqual(
                            [token.value for token in created.spec.api_tokens],
                            [_SECRET],
                        )
                    sent = _request_json("POST", url)["spec"]
                    self.assertIs(sent["allow_unauthenticated_access"], False)
                    self.assertNotIn("api_tokens", sent)

    @responses.activate
    def test_create_allows_empty_or_omitted_tokens_for_server_default(self):
        token_inputs = (
            ("omitted", _UNSET),
            ("empty", []),
        )
        for new_api in (False, True):
            for mode, tokens in token_inputs:
                with self.subTest(new_api=new_api, mode=mode):
                    responses.reset()
                    _register_workspace(new_api=new_api)
                    url = _route(new_api=new_api)
                    responses.add(
                        responses.POST,
                        url,
                        json=_response_body(
                            new_api=new_api,
                            tokens=[_SECRET],
                            allow_unauthenticated_access=False,
                        ),
                        status=201,
                    )

                    created = _client().deployment.create_with_response(
                        _deployment_model(image="nginx", tokens=tokens)
                    )

                    self.assertEqual(
                        [token.value for token in created.spec.api_tokens],
                        [_SECRET],
                    )
                    sent = _request_json("POST", url)["spec"]
                    if tokens is _UNSET:
                        self.assertNotIn("api_tokens", sent)
                    else:
                        self.assertEqual(sent["api_tokens"], [])
                    self.assertNotIn("allow_unauthenticated_access", sent)

    @responses.activate
    def test_contradictory_or_redacted_tokens_fail_before_post(self):
        invalid_requests = (
            _deployment_model(
                image="nginx",
                tokens=["real-token"],
                allow_unauthenticated_access=True,
            ),
            _deployment_model(image="nginx", tokens=["***"]),
        )
        for new_api in (False, True):
            for request in invalid_requests:
                with self.subTest(
                    new_api=new_api,
                    tokens=[token.value for token in request.spec.api_tokens],
                ):
                    responses.reset()
                    _register_workspace(new_api=new_api)
                    with self.assertRaises(ValueError):
                        _client().deployment.create(request)
                    self.assertFalse(
                        any(call.request.method == "POST" for call in responses.calls)
                    )


class TestSecureEndpointDiagnosticContract(unittest.TestCase):
    def test_json_unstructured_token_diagnostics_never_expose_raw_suffix(self):
        raw_suffix = "arbitrary-raw-validator-suffix-6218"
        bodies = (
            json.dumps(f"spec.api_tokens rejected; raw context: {raw_suffix}"),
            json.dumps([
                "spec.apiTokens rejected",
                f"raw context: {raw_suffix}",
            ]),
            json.dumps(
                {"message": f"spec.api_tokens rejected; raw context: {raw_suffix}"}
            ),
        )
        for body in bodies:
            with self.subTest(body=body):
                response = Response()
                response.status_code = 400
                response.encoding = "utf-8"
                response.headers["Content-Type"] = "application/json"
                response._content = body.encode()

                resource = APIResourse.__new__(APIResourse)
                safe = resource._response_for_diagnostic(response)

                self.assertEqual(
                    safe.text,
                    APIResourse._REDACTED_API_TOKEN_DIAGNOSTIC,
                )
                self.assertIn("api_tokens", safe.text)
                self.assertIn("credential", safe.text)
                self.assertIn("redacted", safe.text)
                self.assertNotIn("non-empty", safe.text)
                self.assertNotIn("unauthenticated access", safe.text)
                self.assertNotIn(raw_suffix, safe.text)

    def test_rewritten_plain_text_diagnostic_drops_json_content_type(self):
        response = Response()
        response.status_code = 500
        response.encoding = "utf-8"
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        response._content = b'{"message": "potentially sensitive response"}'

        safe = APIResourse._redacted_response(response)

        self.assertEqual(safe.text, APIResourse._REDACTED_DIAGNOSTIC)
        self.assertNotIn("Content-Type", safe.headers)

    def test_non_json_token_reference_uses_neutral_guidance_without_raw_suffix(self):
        raw_suffix = "internal-validator-suffix-6218"
        response = Response()
        response.status_code = 400
        response.encoding = "utf-8"
        response._content = (
            f"spec.api_tokens must not be empty; raw context: {raw_suffix}"
        ).encode()

        resource = APIResourse.__new__(APIResourse)
        safe = resource._response_for_diagnostic(response)

        self.assertEqual(
            safe.text,
            APIResourse._REDACTED_API_TOKEN_DIAGNOSTIC,
        )
        self.assertIn("api_tokens", safe.text)
        self.assertIn("credential", safe.text)
        self.assertIn("redacted", safe.text)
        self.assertNotIn("non-empty", safe.text)
        self.assertNotIn("unauthenticated access", safe.text)
        self.assertNotIn(raw_suffix, safe.text)
        self.assertNotIn("raw context", safe.text)

    def test_json_known_token_redaction_handles_escaped_and_unicode_text(self):
        token = 'quote" backslash\\ newline\n tab\t snowman-\u2603 caf\u00e9'
        response = Response()
        response.status_code = 400
        response.encoding = "utf-8"
        response._content = json.dumps({
            "message": f"invalid token {token}",
            "apiTokens": [{"value": token}],
        }).encode()

        resource = APIResourse.__new__(APIResourse)
        safe = resource._response_for_diagnostic(
            response,
            sensitive_values=[token],
        )

        self.assertEqual(safe.json()["message"], "invalid token ***")
        self.assertEqual(safe.json()["apiTokens"], [{"value": "***"}])
        self.assertNotIn("snowman", safe.text)
        self.assertNotIn("caf", safe.text)

    def test_nested_non_string_token_value_is_absent_from_pydantic_diagnostic(self):
        malformed_values = (
            {"nested": {"credential": _ESCAPED_SECRET}},
            {"nested": {"credential": _LONG_SECRET}},
            ["wrapper", {"credential": _ESCAPED_SECRET}],
        )
        for malformed_value in malformed_values:
            with self.subTest(value_type=type(malformed_value).__name__):
                raw = _legacy_body()
                raw["spec"]["api_tokens"] = [_malformed_token_entry(malformed_value)]
                response = Response()
                response.status_code = 200
                response.encoding = "utf-8"
                response.headers["Content-Type"] = "application/json"
                response._content = json.dumps(
                    raw,
                    ensure_ascii=False,
                ).encode()

                resource = APIResourse.__new__(APIResourse)
                with self.assertRaises(RuntimeError) as raised:
                    resource.ensure_type(response, LeptonDeployment)

                diagnostic = str(raised.exception)
                _assert_secret_not_rendered(self, diagnostic)
                _assert_secret_not_rendered(self, diagnostic, _LONG_SECRET)
                self.assertIn("primary rotation credential", diagnostic)
                self.assertIn("platform-security", diagnostic)

    def test_nested_non_string_token_value_is_absent_from_list_diagnostic(self):
        malformed_values = (
            {"nested": {"credential": _ESCAPED_SECRET}},
            {"nested": {"credential": _LONG_SECRET}},
            ["wrapper", {"credential": _ESCAPED_SECRET}],
        )
        for malformed_value in malformed_values:
            with self.subTest(value_type=type(malformed_value).__name__):
                raw = _legacy_body()
                raw["spec"]["api_tokens"] = [_malformed_token_entry(malformed_value)]
                response = Response()
                response.status_code = 200
                response.encoding = "utf-8"
                response.headers["Content-Type"] = "application/json"
                response._content = json.dumps(
                    [raw],
                    ensure_ascii=False,
                ).encode()

                resource = APIResourse.__new__(APIResourse)
                stderr = StringIO()
                with redirect_stderr(stderr):
                    parsed = resource.ensure_list(response, LeptonDeployment)

                self.assertEqual(parsed, [])
                diagnostic = stderr.getvalue()
                _assert_secret_not_rendered(self, diagnostic)
                _assert_secret_not_rendered(self, diagnostic, _LONG_SECRET)
                self.assertIn("primary rotation credential", diagnostic)
                self.assertIn("platform-security", diagnostic)

    def test_nested_non_string_token_value_is_absent_from_endpoint_decode_error(self):
        malformed_values = (
            {"nested": {"credential": _ESCAPED_SECRET}},
            {"nested": {"credential": _LONG_SECRET}},
            ["wrapper", {"credential": _ESCAPED_SECRET}],
        )
        for malformed_value in malformed_values:
            with self.subTest(value_type=type(malformed_value).__name__):
                raw = _endpoint_body()
                raw["spec"]["api_tokens"] = [_malformed_token_entry(malformed_value)]

                endpoint_api = EndpointAPI.__new__(EndpointAPI)
                with self.assertRaises(RuntimeError) as raised:
                    endpoint_api._http_endpoint_to_model(raw)

                diagnostic = str(raised.exception)
                _assert_secret_not_rendered(self, diagnostic)
                _assert_secret_not_rendered(self, diagnostic, _LONG_SECRET)
                self.assertIn("endpoint response could not be decoded", diagnostic)

    def test_wrapped_token_value_is_redacted_without_hiding_safe_siblings(self):
        payload = {
            "api_tokens": {
                "items": [{"value": _SECRET}],
                "description": "primary rotation credential",
            }
        }

        self.assertEqual(
            APIResourse._api_token_literal_values(payload),
            [_SECRET],
        )
        redacted = APIResourse._redact_api_token_fields(payload)
        self.assertEqual(redacted["api_tokens"]["items"][0]["value"], "***")
        self.assertEqual(
            redacted["api_tokens"]["description"],
            "primary rotation credential",
        )
        self.assertNotIn(_SECRET, json.dumps(redacted))

    def test_token_redaction_preserves_non_value_sibling_metadata(self):
        token_entry = _malformed_token_entry(
            {"nested": {"credential": _ESCAPED_SECRET}}
        )
        token_entry["value_from"] = {"token_name_ref": "workspace-token-ref"}

        redacted = APIResourse._redact_api_token_fields({"api_tokens": [token_entry]})

        self.assertEqual(redacted["api_tokens"][0]["value"], "***")
        self.assertEqual(
            redacted["api_tokens"][0]["description"],
            "primary rotation credential",
        )
        self.assertEqual(
            redacted["api_tokens"][0]["metadata"],
            {"owner": "platform-security"},
        )
        self.assertEqual(
            redacted["api_tokens"][0]["value_from"],
            {"token_name_ref": "workspace-token-ref"},
        )
        _assert_secret_not_rendered(self, json.dumps(redacted, ensure_ascii=False))

    def test_structured_redaction_preserves_safe_errors_and_metadata(self):
        response = Response()
        response.status_code = 400
        response.encoding = "utf-8"
        response.url = "https://gw.example/request"
        response.reason = "Bad Request"
        response.headers.update({
            "X-Request-ID": "request-123",
            "Retry-After": "7",
            "Set-Cookie": f"session={_SECRET}",
        })
        response.request = type("Request", (), {"body": _SECRET})()
        response._content = json.dumps({
            "message": "spec.api_tokens must not be empty",
            "apiTokens": [{"value": _SECRET}],
        }).encode()

        resource = APIResourse.__new__(APIResourse)
        safe = resource._response_for_diagnostic(response)

        self.assertIn("spec.api_tokens must not be empty", safe.text)
        self.assertNotIn(_SECRET, safe.text)
        self.assertEqual(safe.url, response.url)
        self.assertEqual(safe.reason, response.reason)
        self.assertEqual(safe.headers["X-Request-ID"], "request-123")
        self.assertEqual(safe.headers["Retry-After"], "7")
        self.assertNotIn("Set-Cookie", safe.headers)
        self.assertIsNone(safe.request)

    def test_known_sensitive_values_always_detach_request_metadata(self):
        response = Response()
        response.status_code = 400
        response.encoding = "utf-8"
        response.url = "https://gw.example/request"
        response.reason = "Bad Request"
        response.headers.update({"X-Request-ID": "request-456"})
        original_request = type("Request", (), {"body": _SECRET})()
        response.request = original_request
        response._content = b'{"message": "safe validation failure"}'

        resource = APIResourse.__new__(APIResourse)
        safe = resource._response_for_diagnostic(
            response,
            sensitive_values=[_SECRET],
        )

        self.assertIsNot(safe, response)
        self.assertEqual(safe.json(), {"message": "safe validation failure"})
        self.assertEqual(safe.status_code, 400)
        self.assertEqual(safe.url, response.url)
        self.assertEqual(safe.reason, response.reason)
        self.assertEqual(safe.headers["X-Request-ID"], "request-456")
        self.assertIsNone(safe.request)
        self.assertIs(response.request, original_request)

    def test_list_diagnostic_keeps_reason_while_redacting_token(self):
        resource = APIResourse.__new__(APIResourse)
        item = {
            "metadata": {"name": "broken"},
            "spec": {"api_tokens": [{"value": _SECRET}]},
        }

        diagnostic = resource._format_list_item_error(
            3,
            ValueError(f"missing component after {_SECRET}"),
            item,
        )

        self.assertIn("index 3", diagnostic)
        self.assertIn("missing component", diagnostic)
        self.assertIn("api_tokens", diagnostic)
        self.assertNotIn(_SECRET, diagnostic)

    def test_authentication_opt_out_uses_strict_boolean(self):
        for valid in (True, False, None):
            with self.subTest(valid=valid):
                model = LeptonDeploymentUserSpec(allow_unauthenticated_access=valid)
                self.assertIs(model.allow_unauthenticated_access, valid)

        for invalid in ("true", "false", 1, 0):
            with self.subTest(invalid=invalid):
                with self.assertRaises(Exception):
                    LeptonDeploymentUserSpec(allow_unauthenticated_access=invalid)


class TestPodAuthenticationFieldContract(unittest.TestCase):
    @responses.activate
    def test_pod_create_rejects_endpoint_auth_field_before_mutation(self):
        for new_api in (False, True):
            for allow_unauthenticated_access in (False, True):
                with self.subTest(
                    new_api=new_api,
                    allow_unauthenticated_access=allow_unauthenticated_access,
                ):
                    responses.reset()
                    _register_workspace(new_api=new_api)
                    client = _client()

                    with self.assertRaisesRegex(
                        ValueError,
                        "applies only to endpoints",
                    ):
                        client.pod.create(
                            _pod_model(
                                allow_unauthenticated_access=(
                                    allow_unauthenticated_access
                                )
                            )
                        )

                    self.assertEqual(
                        [
                            call.request.method
                            for call in responses.calls
                            if call.request.method in {"POST", "PUT", "PATCH"}
                        ],
                        [],
                    )

    @responses.activate
    def test_legacy_deployment_api_rejects_auth_field_for_all_pod_mutations(self):
        operations = ("create", "create_with_response", "create_pod", "update")
        for operation in operations:
            for allow_unauthenticated_access in (False, True):
                with self.subTest(
                    operation=operation,
                    allow_unauthenticated_access=allow_unauthenticated_access,
                ):
                    responses.reset()
                    _register_workspace(new_api=False)
                    api = _client().deployment
                    pod = _pod_model(
                        allow_unauthenticated_access=allow_unauthenticated_access
                    )

                    with self.assertRaisesRegex(
                        ValueError,
                        "applies only to endpoints",
                    ):
                        if operation == "update":
                            api.update("pod", pod)
                        else:
                            getattr(api, operation)(pod)

                    self.assertEqual(
                        [
                            call.request.method
                            for call in responses.calls
                            if call.request.method in {"POST", "PUT", "PATCH"}
                        ],
                        [],
                    )


class TestSecureEndpointUpdateContract(unittest.TestCase):
    def _register_update(self, *, new_api, existing, updated):
        url = _route(new_api=new_api, name="ep")
        if new_api:
            responses.add(responses.GET, url, json=existing, status=200)
        responses.add(responses.PATCH, url, json=updated, status=200)
        return url

    @responses.activate
    def test_incomplete_authentication_updates_fail_before_patch(self):
        invalid_updates = (
            (
                "empty tokens without opt-out",
                _deployment_model(tokens=[]),
                "Clearing API tokens requires",
            ),
            (
                "protected mode without tokens",
                _deployment_model(allow_unauthenticated_access=False),
                "requires at least one API token",
            ),
        )
        for new_api in (False, True):
            for mode, update, expected_message in invalid_updates:
                with self.subTest(new_api=new_api, mode=mode):
                    responses.reset()
                    _register_workspace(new_api=new_api)
                    url = _route(new_api=new_api, name="ep")
                    if new_api:
                        responses.add(
                            responses.GET,
                            url,
                            json=_endpoint_body(
                                tokens=["old-token"],
                                allow_unauthenticated_access=False,
                            ),
                            status=200,
                        )

                    with self.assertRaisesRegex(ValueError, expected_message):
                        _client().deployment.update("ep", update)

                    self.assertFalse(
                        any(call.request.method == "PATCH" for call in responses.calls)
                    )

    # LEP-6218: protected-to-unauthenticated and the reverse transition each
    # travel in one valid PATCH for both API families.
    @responses.activate
    def test_authentication_mode_transitions_are_atomic(self):
        transitions = (
            (
                "protected to unauthenticated",
                ["old-token"],
                False,
                [],
                True,
            ),
            (
                "unauthenticated to protected",
                [],
                True,
                ["new-token"],
                False,
            ),
            (
                "replace protected tokens",
                ["old-token"],
                False,
                ["replacement-a", "replacement-b"],
                False,
            ),
        )
        for new_api in (False, True):
            for (
                transition,
                old_tokens,
                old_allow,
                new_tokens,
                new_allow,
            ) in transitions:
                with self.subTest(new_api=new_api, transition=transition):
                    responses.reset()
                    _register_workspace(new_api=new_api)
                    url = self._register_update(
                        new_api=new_api,
                        existing=_response_body(
                            new_api=new_api,
                            tokens=old_tokens,
                            allow_unauthenticated_access=old_allow,
                        ),
                        updated=_response_body(
                            new_api=new_api,
                            tokens=new_tokens,
                            allow_unauthenticated_access=new_allow,
                        ),
                    )

                    updated = _client().deployment.update(
                        "ep",
                        _deployment_model(
                            tokens=new_tokens,
                            allow_unauthenticated_access=new_allow,
                        ),
                    )

                    sent = _request_json("PATCH", url)["spec"]
                    self.assertEqual(sent["api_tokens"], _token_dicts(new_tokens))
                    self.assertIs(
                        sent["allow_unauthenticated_access"],
                        new_allow,
                    )
                    self.assertEqual(
                        [token.value for token in updated.spec.api_tokens],
                        new_tokens,
                    )
                    self.assertIs(
                        updated.spec.allow_unauthenticated_access,
                        new_allow,
                    )

    # LEP-6218: an unrelated PATCH omits both authentication fields even when
    # the live resource currently contains them.
    @responses.activate
    def test_unrelated_update_omits_authentication_fields(self):
        live_modes = (
            (["existing-token"], False),
            ([], True),
        )
        for new_api in (False, True):
            for live_tokens, live_allow in live_modes:
                with self.subTest(
                    new_api=new_api,
                    live_allow=live_allow,
                ):
                    responses.reset()
                    _register_workspace(new_api=new_api)
                    url = self._register_update(
                        new_api=new_api,
                        existing=_response_body(
                            new_api=new_api,
                            tokens=live_tokens,
                            allow_unauthenticated_access=live_allow,
                        ),
                        updated=_response_body(
                            new_api=new_api,
                            tokens=live_tokens,
                            allow_unauthenticated_access=live_allow,
                            image="nginx:new",
                        ),
                    )

                    _client().deployment.update(
                        "ep",
                        _deployment_model(image="nginx:new"),
                    )

                    sent = _request_json("PATCH", url)["spec"]
                    self.assertNotIn("api_tokens", sent)
                    self.assertNotIn("allow_unauthenticated_access", sent)


if __name__ == "__main__":
    unittest.main()
