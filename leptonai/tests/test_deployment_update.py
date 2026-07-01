import unittest

from leptonai.api.v2.deployment import DeploymentAPI
from leptonai.api.v2.types.common import Metadata
from leptonai.api.v2.types.deployment import (
    LeptonDeployment,
    LeptonDeploymentUserSpec,
)


class TestLoadBalanceUpdatePayload(unittest.TestCase):
    """The backend applies updates as a JSON merge patch, so switching the load
    balance policy requires the deselected sub-field to be sent as an explicit
    null. The CLI builds load_balance_config as a raw dict (assigned after the
    spec is constructed) precisely so safe_json's exclude_none does not drop
    that null. These tests lock in that update() preserves it on the wire.
    """

    def _capture_update_payload(self, load_balance_config):
        api = DeploymentAPI.__new__(DeploymentAPI)
        captured = {}

        def fake_patch(url, json=None, **kwargs):
            captured["json"] = json
            return "ok"

        api._patch = fake_patch
        api.ensure_type = lambda response, typ: response

        # Mirror the CLI: assign the raw dict AFTER construction so pydantic
        # keeps it as a dict instead of coercing it into LoadBalanceConfig
        # (which would re-introduce the exclude_none null-dropping).
        spec = LeptonDeploymentUserSpec()
        spec.load_balance_config = load_balance_config
        dep = LeptonDeployment(metadata=Metadata(id="ep", name="ep"), spec=spec)
        api.update("ep", dep)
        return captured["json"]["spec"]["load_balance_config"]

    def test_switch_to_sticky_routing_clears_least_request(self):
        payload = self._capture_update_payload({"least_request": None, "maglev": {}})
        # explicit null clears the previous policy under JSON merge patch
        self.assertIn("least_request", payload)
        self.assertIsNone(payload["least_request"])
        self.assertEqual(payload["maglev"], {})

    def test_switch_to_least_request_clears_maglev(self):
        payload = self._capture_update_payload({"least_request": {}, "maglev": None})
        self.assertIn("maglev", payload)
        self.assertIsNone(payload["maglev"])
        # The selected policy is sent as an empty object: it selects least-request
        # by presence without sending nested nulls that would clobber a
        # previously configured option (e.g. choice_count) under merge patch.
        self.assertEqual(payload["least_request"], {})

    def test_update_without_load_balance_omits_field(self):
        # An update that does not touch the load balance policy must not send
        # the field at all, otherwise the merge patch would clobber it.
        api = DeploymentAPI.__new__(DeploymentAPI)
        captured = {}

        def fake_patch(url, json=None, **kwargs):
            captured["json"] = json
            return "ok"

        api._patch = fake_patch
        api.ensure_type = lambda response, typ: response

        dep = LeptonDeployment(
            metadata=Metadata(id="ep", name="ep"),
            spec=LeptonDeploymentUserSpec(),
        )
        api.update("ep", dep)
        self.assertNotIn("load_balance_config", captured["json"].get("spec", {}))


if __name__ == "__main__":
    unittest.main()
