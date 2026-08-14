"""Concurrency and isolation tests for new-deployment-API flag caching."""

import os
import tempfile
import threading
import unittest
import unittest.mock
from types import SimpleNamespace

# Never consult a developer's real workspace record while constructing clients.
os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

from pydantic import ValidationError

import leptonai.api.v2 as api_v2
from leptonai.api.v2 import client as client_module
from leptonai.api.v2.client import APIClient
from leptonai.api.v2.types.workspace import WorkspaceFeatures
from leptonai.cli.util import _get_only_replica_public_ip


BASE = "https://gw.example/api/v2/workspaces/ws1"
OTHER_BASE = "https://gw.example/api/v2/workspaces/ws2"


def _client(url=BASE, token="token"):
    return APIClient(
        workspace_id="ws1",
        auth_token=token,
        url=url,
        workspace_origin_url="https://console.example",
    )


class TestNewDeploymentAPIFlagCache(unittest.TestCase):
    def setUp(self):
        client_module.reset_new_deployment_api_flag_cache()

    def tearDown(self):
        client_module.reset_new_deployment_api_flag_cache()

    def test_cache_isolated_by_non_reversible_credential_fingerprint(self):
        resolutions = []

        def resolve(client):
            resolutions.append(client.auth_token)
            return client.auth_token == "fresh-token"

        stale = _client(token="stale-token")
        fresh = _client(token="fresh-token")
        with unittest.mock.patch.object(
            APIClient, "_resolve_new_deployment_api", resolve
        ):
            self.assertFalse(stale.new_deployment_api_enabled)
            self.assertTrue(fresh.new_deployment_api_enabled)
            self.assertFalse(stale.new_deployment_api_enabled)
            self.assertTrue(fresh.new_deployment_api_enabled)

        self.assertCountEqual(resolutions, ["stale-token", "fresh-token"])
        cache_keys = list(client_module._NEW_DEPLOYMENT_API_FLAG_CACHE)
        self.assertEqual(len(cache_keys), 2)
        self.assertEqual({key[0] for key in cache_keys}, {BASE})
        for _, fingerprint in cache_keys:
            self.assertEqual(len(fingerprint), 64)
            self.assertNotIn("stale-token", fingerprint)
            self.assertNotIn("fresh-token", fingerprint)

        unauthenticated = client_module._new_deployment_api_credential_fingerprint(None)
        self.assertEqual(
            unauthenticated,
            client_module._new_deployment_api_credential_fingerprint(None),
        )

    def test_same_key_resolves_exactly_once(self):
        clients = [_client(token="shared-token") for _ in range(12)]
        start = threading.Barrier(len(clients))
        entered = threading.Event()
        release = threading.Event()
        resolution_count = 0
        count_lock = threading.Lock()
        results = []
        errors = []

        def resolve(_client):
            nonlocal resolution_count
            with count_lock:
                resolution_count += 1
            entered.set()
            if not release.wait(timeout=2):
                raise AssertionError("test did not release flag resolution")
            return True

        def read_flag(client):
            try:
                start.wait(timeout=2)
                results.append(client.new_deployment_api_enabled)
            except BaseException as exc:
                errors.append(exc)

        with unittest.mock.patch.object(
            APIClient, "_resolve_new_deployment_api", resolve
        ):
            threads = [threading.Thread(target=read_flag, args=(c,)) for c in clients]
            for thread in threads:
                thread.start()
            self.assertTrue(entered.wait(timeout=2))
            release.set()
            for thread in threads:
                thread.join(timeout=2)
                self.assertFalse(thread.is_alive())

        self.assertEqual(errors, [])
        self.assertEqual(resolution_count, 1)
        self.assertEqual(results, [True] * len(clients))

    def test_different_keys_resolve_concurrently_without_convoy(self):
        scenarios = {
            "different-workspaces": [
                _client(url=BASE, token="token-a"),
                _client(url=OTHER_BASE, token="token-a"),
            ],
            "same-workspace-different-credentials": [
                _client(url=BASE, token="token-a"),
                _client(url=BASE, token="token-b"),
            ],
        }

        for scenario, clients in scenarios.items():
            with self.subTest(scenario=scenario):
                client_module.reset_new_deployment_api_flag_cache()
                both_resolving = threading.Barrier(2)
                results = {}
                errors = []

                def resolve(client):
                    # This barrier can only complete if no global mutex is held
                    # across resolution. A serialized implementation times out.
                    both_resolving.wait(timeout=2)
                    return client.auth_token == "token-a"

                def read_flag(client):
                    try:
                        identity = (client.url, client.auth_token)
                        results[identity] = client.new_deployment_api_enabled
                    except BaseException as exc:
                        errors.append(exc)

                with unittest.mock.patch.object(
                    APIClient, "_resolve_new_deployment_api", resolve
                ):
                    threads = [
                        threading.Thread(target=read_flag, args=(c,)) for c in clients
                    ]
                    for thread in threads:
                        thread.start()
                    for thread in threads:
                        thread.join(timeout=3)
                        self.assertFalse(thread.is_alive())

                self.assertEqual(errors, [])
                self.assertEqual(len(results), 2)
                for client in clients:
                    self.assertEqual(
                        results[(client.url, client.auth_token)],
                        client.auth_token == "token-a",
                    )

    def test_url_and_global_resets_clear_all_matching_credentials(self):
        outcomes = {
            (BASE, "token-a"): False,
            (BASE, "token-b"): True,
            (OTHER_BASE, "token-c"): True,
        }
        resolutions = []

        def resolve(client):
            identity = (client.url, client.auth_token)
            resolutions.append(identity)
            return outcomes[identity]

        first = _client(token="token-a")
        second = _client(token="token-b")
        other = _client(url=OTHER_BASE, token="token-c")
        with unittest.mock.patch.object(
            APIClient, "_resolve_new_deployment_api", resolve
        ):
            self.assertFalse(first.new_deployment_api_enabled)
            self.assertTrue(second.new_deployment_api_enabled)
            self.assertTrue(other.new_deployment_api_enabled)

            outcomes[(BASE, "token-a")] = True
            outcomes[(BASE, "token-b")] = False
            outcomes[(OTHER_BASE, "token-c")] = False
            client_module.reset_new_deployment_api_flag_cache(BASE)

            self.assertTrue(first.new_deployment_api_enabled)
            self.assertFalse(second.new_deployment_api_enabled)
            # URL-scoped reset leaves the other workspace's entry intact.
            self.assertTrue(other.new_deployment_api_enabled)

            client_module.reset_new_deployment_api_flag_cache()
            self.assertFalse(other.new_deployment_api_enabled)

        self.assertEqual(resolutions.count((BASE, "token-a")), 2)
        self.assertEqual(resolutions.count((BASE, "token-b")), 2)
        self.assertEqual(resolutions.count((OTHER_BASE, "token-c")), 2)

    def test_reset_waits_for_inflight_result_then_removes_it(self):
        for reset_scope in (BASE, None):
            with self.subTest(reset_scope=reset_scope):
                client_module.reset_new_deployment_api_flag_cache()
                client = _client()
                entered = threading.Event()
                release = threading.Event()
                reset_done = threading.Event()
                resolutions = 0
                result = []

                def resolve(_client):
                    nonlocal resolutions
                    resolutions += 1
                    if resolutions == 1:
                        entered.set()
                        if not release.wait(timeout=2):
                            raise AssertionError("test did not release flag resolution")
                        return False
                    return True

                def reset_cache():
                    client_module.reset_new_deployment_api_flag_cache(reset_scope)
                    reset_done.set()

                with unittest.mock.patch.object(
                    APIClient, "_resolve_new_deployment_api", resolve
                ):
                    reader = threading.Thread(
                        target=lambda: result.append(client.new_deployment_api_enabled)
                    )
                    reader.start()
                    self.assertTrue(entered.wait(timeout=2))

                    resetter = threading.Thread(target=reset_cache)
                    resetter.start()
                    with client_module._FLAG_CACHE_CONDITION:
                        self.assertTrue(
                            client_module._FLAG_CACHE_CONDITION.wait_for(
                                lambda: (
                                    bool(client_module._FLAG_CACHE_RESETTING_ALL)
                                    if reset_scope is None
                                    else bool(
                                        client_module._FLAG_CACHE_RESETTING_URLS.get(
                                            BASE
                                        )
                                    )
                                ),
                                timeout=2,
                            )
                        )
                    self.assertFalse(reset_done.is_set())

                    release.set()
                    reader.join(timeout=2)
                    resetter.join(timeout=2)
                    self.assertFalse(reader.is_alive())
                    self.assertFalse(resetter.is_alive())
                    self.assertTrue(reset_done.is_set())
                    self.assertEqual(result, [False])

                    # The pre-reset False was removed rather than reappearing.
                    self.assertTrue(client.new_deployment_api_enabled)
                    self.assertEqual(resolutions, 2)

    def test_after_fork_helper_drops_inflight_state_but_keeps_cache(self):
        cache_key = (
            BASE,
            client_module._new_deployment_api_credential_fingerprint("token"),
        )
        old_condition = client_module._FLAG_CACHE_CONDITION
        with old_condition:
            client_module._NEW_DEPLOYMENT_API_FLAG_CACHE[cache_key] = True
            client_module._FLAG_CACHE_RESOLVING.add(cache_key)
            client_module._FLAG_CACHE_RESETTING_URLS[BASE] = 1
            client_module._FLAG_CACHE_RESETTING_ALL = 1

        client_module._reset_new_deployment_api_flag_cache_after_fork()

        self.assertIsNot(client_module._FLAG_CACHE_CONDITION, old_condition)
        self.assertEqual(
            client_module._NEW_DEPLOYMENT_API_FLAG_CACHE, {cache_key: True}
        )
        self.assertEqual(client_module._FLAG_CACHE_RESOLVING, set())
        self.assertEqual(client_module._FLAG_CACHE_RESETTING_URLS, {})
        self.assertEqual(client_module._FLAG_CACHE_RESETTING_ALL, 0)

    def test_resolution_uses_bounded_timeout_on_every_attempt(self):
        client = _client()

        with (
            unittest.mock.patch.object(
                client, "info", side_effect=RuntimeError("workspace unavailable")
            ) as info,
            unittest.mock.patch.object(client_module.time, "sleep"),
        ):
            self.assertFalse(client._resolve_new_deployment_api())

        self.assertEqual(
            info.call_args_list,
            [
                unittest.mock.call(
                    timeout=client_module._FLAG_RESOLVE_REQUEST_TIMEOUT_SECONDS
                )
            ]
            * (client_module._FLAG_RESOLVE_RETRIES + 1),
        )
        self.assertEqual(client_module._FLAG_RESOLVE_REQUEST_TIMEOUT_SECONDS, 5.0)

    def test_info_forwards_optional_timeout_without_changing_default(self):
        client = _client()
        response = unittest.mock.Mock(status_code=200)
        workspace_info = object()

        with (
            unittest.mock.patch.object(client, "_get", return_value=response) as get,
            unittest.mock.patch.object(
                client_module.APIResourse, "ensure_type", return_value=workspace_info
            ),
        ):
            self.assertIs(client.info(timeout=2.5), workspace_info)
            get.assert_called_once_with("/workspace", timeout=2.5)

        with (
            unittest.mock.patch.object(client, "_get", return_value=response) as get,
            unittest.mock.patch.object(
                client_module.APIResourse, "ensure_type", return_value=workspace_info
            ),
        ):
            self.assertIs(client.info(), workspace_info)
            get.assert_called_once_with("/workspace")

    def test_deployment_and_pod_properties_accept_injected_overrides(self):
        client = _client()
        deployment_override = object()
        pod_override = object()

        client.deployment = deployment_override
        client.pod = pod_override

        # Reading an override must not resolve the feature flag as a side effect.
        with unittest.mock.patch.object(
            APIClient,
            "_resolve_new_deployment_api",
            side_effect=AssertionError("override unexpectedly resolved the flag"),
        ):
            self.assertIs(client.deployment, deployment_override)
            self.assertIs(client.pod, pod_override)

    def test_patch_object_restores_deployment_and_pod_dispatch(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                client = _client(token=f"dispatch-{enabled}")
                expected_deployment = (
                    client._endpoint_api if enabled else client._deployment_legacy
                )
                expected_pod = client._devpod_api if enabled else client._pod_legacy

                with unittest.mock.patch.object(
                    APIClient, "_resolve_new_deployment_api", return_value=enabled
                ) as resolve:
                    with unittest.mock.patch.object(
                        client, "deployment", object()
                    ) as fake:
                        self.assertIs(client.deployment, fake)
                    self.assertIs(client.deployment, expected_deployment)
                    self.assertNotIn("deployment", client.__dict__)
                    self.assertIs(
                        client._deployment_override,
                        client_module._API_RESOURCE_OVERRIDE_UNSET,
                    )

                    with unittest.mock.patch.object(client, "pod", object()) as fake:
                        self.assertIs(client.pod, fake)
                    self.assertIs(client.pod, expected_pod)
                    self.assertNotIn("pod", client.__dict__)
                    self.assertIs(
                        client._pod_override,
                        client_module._API_RESOURCE_OVERRIDE_UNSET,
                    )

                # The first patch lookup resolves the process memo. Restoration
                # reuses that decision rather than leaving an override behind.
                resolve.assert_called_once_with()

    def test_nested_patch_object_restores_existing_public_overrides(self):
        client = _client()

        with unittest.mock.patch.object(
            APIClient,
            "_resolve_new_deployment_api",
            side_effect=AssertionError("an explicit override resolved the flag"),
        ):
            for attribute in ("deployment", "pod"):
                with self.subTest(attribute=attribute):
                    outer = object()
                    inner = object()
                    setattr(client, attribute, outer)

                    self.assertIs(client.__dict__[attribute], outer)
                    with unittest.mock.patch.object(client, attribute, inner):
                        self.assertIs(getattr(client, attribute), inner)
                        self.assertIs(client.__dict__[attribute], inner)

                    self.assertIs(getattr(client, attribute), outer)
                    self.assertIs(client.__dict__[attribute], outer)

                    delattr(client, attribute)
                    self.assertNotIn(attribute, client.__dict__)

    def test_endpoint_pod_creation_honors_public_pod_override(self):
        client = _client()
        pod_override = unittest.mock.Mock()
        pod_override.create.side_effect = ["create-result", "create-pod-result"]
        client.pod = pod_override
        pod_spec = SimpleNamespace(spec=SimpleNamespace(is_pod=True))
        create_pod_spec = SimpleNamespace(spec=SimpleNamespace(is_pod=False))

        with (
            unittest.mock.patch.object(
                client._devpod_api,
                "create",
                side_effect=AssertionError("EndpointAPI bypassed client.pod"),
            ),
            unittest.mock.patch.object(
                APIClient,
                "_resolve_new_deployment_api",
                side_effect=AssertionError("pod override unexpectedly resolved flag"),
            ),
        ):
            self.assertEqual(client._endpoint_api.create(pod_spec), "create-result")
            with self.assertWarns(DeprecationWarning):
                self.assertEqual(
                    client._endpoint_api.create_pod(create_pod_spec),
                    "create-pod-result",
                )

        self.assertTrue(create_pod_spec.spec.is_pod)
        self.assertEqual(
            pod_override.create.call_args_list,
            [unittest.mock.call(pod_spec), unittest.mock.call(create_pod_spec)],
        )

    def test_public_ip_helper_honors_new_pod_override(self):
        client = _client(token="new-pod-override")
        pod_override = unittest.mock.Mock()
        pod_override.get.return_value = SimpleNamespace(
            status=SimpleNamespace(public_ip="203.0.113.10")
        )
        client.pod = pod_override

        with (
            unittest.mock.patch.object(
                APIClient, "_resolve_new_deployment_api", return_value=True
            ),
            unittest.mock.patch.object(
                client._devpod_api,
                "get",
                side_effect=AssertionError("helper bypassed client.pod"),
            ),
        ):
            self.assertEqual(
                _get_only_replica_public_ip("pod-name", client), "203.0.113.10"
            )

        pod_override.get.assert_called_once_with("pod-name")

    def test_public_ip_helper_honors_legacy_deployment_override(self):
        client = _client(token="legacy-deployment-override")
        deployment_override = unittest.mock.Mock()
        deployment_override.get_replicas.return_value = [
            SimpleNamespace(status=SimpleNamespace(public_ip="203.0.113.11"))
        ]
        client.deployment = deployment_override

        with (
            unittest.mock.patch.object(
                APIClient, "_resolve_new_deployment_api", return_value=False
            ),
            unittest.mock.patch.object(
                client._deployment_legacy,
                "get_replicas",
                side_effect=AssertionError(
                    "helper bypassed the legacy deployment override accessor"
                ),
            ),
        ):
            self.assertEqual(
                _get_only_replica_public_ip("pod-name", client), "203.0.113.11"
            )

        deployment_override.get_replicas.assert_called_once_with("pod-name")

    def test_legacy_pod_delegation_honors_explicit_deployment_wrapper(self):
        client = _client()
        deployment = unittest.mock.Mock()
        replica = object()
        deployment.get.return_value = "get-result"
        deployment.delete.return_value = "delete-result"
        deployment.stop.return_value = "stop-result"
        deployment.restart.return_value = "restart-result"
        deployment.get_readiness.return_value = "readiness-result"
        deployment.get_termination.return_value = "termination-result"
        deployment.get_replicas.return_value = [replica]
        deployment.get_log.return_value = iter(["log-result"])
        client.deployment = deployment

        pod = client._pod_legacy
        self.assertEqual(pod.get("pod"), "get-result")
        self.assertEqual(pod.delete("pod"), "delete-result")
        self.assertEqual(pod.stop("pod"), "stop-result")
        self.assertEqual(pod.restart("pod"), "restart-result")
        self.assertEqual(pod.get_readiness("pod"), "readiness-result")
        self.assertEqual(pod.get_termination("pod"), "termination-result")
        self.assertEqual(list(pod.get_log("pod", timeout=7)), ["log-result"])

        deployment.get.assert_called_once_with("pod")
        deployment.delete.assert_called_once_with("pod")
        deployment.stop.assert_called_once_with("pod")
        deployment.restart.assert_called_once_with("pod")
        deployment.get_readiness.assert_called_once_with("pod")
        deployment.get_termination.assert_called_once_with("pod")
        deployment.get_replicas.assert_called_once_with("pod")
        deployment.get_log.assert_called_once_with("pod", replica, 7)

    def test_legacy_pod_delegation_stays_legacy_without_override(self):
        client = _client()

        with (
            unittest.mock.patch.object(
                client._deployment_legacy, "get", return_value="legacy-result"
            ) as legacy_get,
            unittest.mock.patch.object(
                client._endpoint_api,
                "get",
                side_effect=AssertionError("legacy PodAPI dispatched to EndpointAPI"),
            ),
            unittest.mock.patch.object(
                APIClient,
                "_resolve_new_deployment_api",
                side_effect=AssertionError("legacy PodAPI resolved the feature flag"),
            ),
        ):
            self.assertEqual(client._pod_legacy.get("pod"), "legacy-result")

        legacy_get.assert_called_once_with("pod")


class TestWorkspaceFlagSchema(unittest.TestCase):
    def test_flag_accepts_only_strict_boolean_values(self):
        self.assertTrue(
            WorkspaceFeatures(enable_new_deployment_api=True).enable_new_deployment_api
        )
        self.assertFalse(
            WorkspaceFeatures(enable_new_deployment_api=False).enable_new_deployment_api
        )
        self.assertIsNone(WorkspaceFeatures().enable_new_deployment_api)

        for invalid in ("true", "false", 1, 0):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValidationError):
                    WorkspaceFeatures(enable_new_deployment_api=invalid)

    def test_reset_hook_is_exported_from_public_api(self):
        self.assertIs(
            api_v2.reset_new_deployment_api_flag_cache,
            client_module.reset_new_deployment_api_flag_cache,
        )


if __name__ == "__main__":
    unittest.main()
