"""Public HTTP/SDK contract tests for LEP-6218 endpoint authentication."""

import json
import os
import tempfile
import unittest

# Tests must never read a developer's real workspace configuration.
os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

import responses

from leptonai.api.v2 import client as client_module
from leptonai.api.v2.api_resource import ClientError, ServerError
from leptonai.api.v2.client import APIClient
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

    # LEP-6218 security: response-returning create cannot reliably identify a
    # markerless generated credential, so every downstream error is generic.
    @responses.activate
    def test_create_with_response_redacts_markerless_downstream_errors(self):
        for new_api in (False, True):
            for status, error_type in (
                (400, ClientError),
                (500, ServerError),
            ):
                with self.subTest(new_api=new_api, status=status):
                    responses.reset()
                    _register_workspace(new_api=new_api)
                    url = _route(new_api=new_api)
                    responses.add(
                        responses.POST,
                        url,
                        body=f"downstream failure {_SECRET}",
                        status=status,
                        content_type="text/plain",
                    )

                    with self.assertRaises(error_type) as raised:
                        _client().deployment.create_with_response(
                            _deployment_model(image="nginx")
                        )

                    self.assertNotIn(_SECRET, str(raised.exception))
                    self.assertNotIn(_SECRET, raised.exception.response.text)
                    self.assertEqual(raised.exception.response.status_code, status)


class TestSecureEndpointUpdateContract(unittest.TestCase):
    def _register_update(self, *, new_api, existing, updated):
        url = _route(new_api=new_api, name="ep")
        if new_api:
            responses.add(responses.GET, url, json=existing, status=200)
        responses.add(responses.PATCH, url, json=updated, status=200)
        return url

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
