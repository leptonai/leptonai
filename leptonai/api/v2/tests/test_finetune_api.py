"""HTTP contract for FineTuneAPI.list_supported_models."""

import os
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("LEPTON_CACHE_DIR", tempfile.mkdtemp())

import responses

from leptonai.api.v2.client import APIClient

BASE = "https://gw.example/api/v2/workspaces/ws1"
SUPPORTED_MODELS = f"{BASE}/finetune/supported-models"


def _client():
    return APIClient(workspace_id="ws1", auth_token="tok", url=BASE)


def _query(request):
    return parse_qs(urlparse(request.url).query)


class TestFineTuneListSupportedModels(unittest.TestCase):
    @responses.activate
    def test_list_supported_models_defaults_to_automodel_trainer(self):
        responses.add(
            responses.GET,
            SUPPORTED_MODELS,
            json=[{
                "model_id": "meta-llama/Llama-3.2-1B",
                "sft": {"is_supported": True},
                "lora": {"is_supported": None},
            }],
            status=200,
        )

        models = _client().finetune.list_supported_models()

        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(_query(responses.calls[0].request), {"trainer": ["automodel"]})
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0].model_id, "meta-llama/Llama-3.2-1B")
        self.assertTrue(models[0].sft.is_supported)
        self.assertIsNone(models[0].lora.is_supported)

    @responses.activate
    def test_list_supported_models_sends_given_trainer(self):
        responses.add(responses.GET, SUPPORTED_MODELS, json=[], status=200)

        models = _client().finetune.list_supported_models(trainer="custom")

        self.assertEqual(_query(responses.calls[0].request), {"trainer": ["custom"]})
        self.assertEqual(models, [])


if __name__ == "__main__":
    unittest.main()
