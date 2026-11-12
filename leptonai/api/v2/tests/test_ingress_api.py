"""HTTP contract for IngressAPI.create_endpoint."""

import json
import os
import tempfile
import unittest

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

import responses

from leptonai.api.v2.client import APIClient
from leptonai.api.v2.types.ingress import LeptonIngressEndpoint

BASE = "https://gw.example/api/v2/workspaces/ws1"


def _client():
    return APIClient(workspace_id="ws1", auth_token="tok", url=BASE)


def _ingress_body():
    return {
        "metadata": {"id": "ing-1", "name": "ing-1"},
        "spec": {
            "domain_name": "example.com",
            "endpoints": [{"deployment": "ep-1", "weight": 100}],
        },
    }


class TestIngressCreateEndpoint(unittest.TestCase):
    @responses.activate
    def test_create_endpoint_wraps_request_body_in_spec(self):
        responses.add(
            responses.POST,
            f"{BASE}/ingress/ing-1/endpoint/deployment",
            json=_ingress_body(),
            status=200,
        )

        ingress = _client().ingress.create_endpoint(
            "ing-1",
            LeptonIngressEndpoint(deployment="ep-1", weight=100),
        )

        self.assertEqual(len(responses.calls), 1)
        request = responses.calls[0].request
        self.assertEqual(request.url, f"{BASE}/ingress/ing-1/endpoint/deployment")
        self.assertEqual(
            json.loads(request.body),
            {"spec": {"deployment": "ep-1", "weight": 100}},
        )
        self.assertEqual(ingress.metadata.id_, "ing-1")
        self.assertEqual(ingress.spec.endpoints[0].deployment, "ep-1")
        self.assertEqual(ingress.spec.endpoints[0].weight, 100)


if __name__ == "__main__":
    unittest.main()
