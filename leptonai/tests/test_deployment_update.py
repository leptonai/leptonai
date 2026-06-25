import unittest

from leptonai.api.v1.deployment import DeploymentAPI
from leptonai.api.v1.types.common import Metadata
from leptonai.api.v1.types.deployment import (
    LeptonDeployment,
    LeptonDeploymentUserSpec,
)
from leptonai.api.v1.types.ingress import (
    LeastRequestLoadBalancer,
    LoadBalanceConfig,
    MaglevLoadBalancer,
)


class TestLoadBalanceUpdatePayload(unittest.TestCase):
    """The backend applies updates as a JSON merge patch, so switching the load
    balance policy requires the deselected sub-field to be sent as an explicit
    null. exclude_none in safe_json would drop it, leaving the old policy in
    place (and producing a 400 "no valid field to update" on the revert). These
    tests lock in that update() preserves the null.
    """

    def _capture_update_payload(self, load_balance_config):
        api = DeploymentAPI.__new__(DeploymentAPI)
        captured = {}

        def fake_patch(url, json=None, **kwargs):
            captured["json"] = json
            return "ok"

        api._patch = fake_patch
        api.ensure_type = lambda response, typ: response

        spec = LeptonDeploymentUserSpec(load_balance_config=load_balance_config)
        dep = LeptonDeployment(metadata=Metadata(id="ep", name="ep"), spec=spec)
        api.update("ep", dep)
        return captured["json"]["spec"]["load_balance_config"]

    def test_switch_to_sticky_routing_clears_least_request(self):
        payload = self._capture_update_payload(
            LoadBalanceConfig(maglev=MaglevLoadBalancer())
        )
        # explicit null clears the previous policy under JSON merge patch
        self.assertIn("least_request", payload)
        self.assertIsNone(payload["least_request"])
        self.assertEqual(payload["maglev"], {})

    def test_switch_to_least_request_clears_maglev(self):
        payload = self._capture_update_payload(
            LoadBalanceConfig(least_request=LeastRequestLoadBalancer())
        )
        self.assertIn("maglev", payload)
        self.assertIsNone(payload["maglev"])
        self.assertIsNotNone(payload["least_request"])

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
