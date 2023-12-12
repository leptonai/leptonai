import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest

from leptonai import Client
from leptonai.photon import create, load_metadata
from utils import random_name, photon_run_local_server


class TestvLLM(unittest.TestCase):
    def test_photon_file_metadata(self):
        name = random_name()
        model = "vllm:gpt2"
        ph = create(name, model)
        path = ph.save()
        metadata = load_metadata(path)
        self.assertEqual(metadata["name"], name)
        self.assertTrue(metadata["model"].startswith(model))
        self.assertTrue("image" in metadata)
        self.assertTrue("args" in metadata)
        self.assertTrue("openapi_schema" in metadata)
        self.assertTrue("py_obj" not in metadata)

    def test_run_vllm_photon(self):
        import torch

        if not torch.cuda.is_available():
            raise unittest.SkipTest("Skipping test because CUDA is not available")
        model = "vllm:gpt2"
        proc, port = photon_run_local_server(name=random_name(), model=model)
        client = Client(f"http://127.0.0.1:{port}")

        # completions api
        resp = client.api.v1.completions(
            model="gpt2",
            prompt="Hello world",
            max_tokens=10,
        )
        self.assertIn("choices", resp)
        self.assertEqual(len(resp["choices"]), 1)
        self.assertIn("text", resp["choices"][0])
        self.assertIn("finish_reason", resp["choices"][0])
        self.assertIn("usage", resp)

        # chat completions api
        resp = client.api.v1.chat.completions(
            model="gpt2",
            messages=[
                {"role": "user", "content": "Give me a 3 days travel plan for Hawaii"},
            ],
            max_tokens=10,
        )
        self.assertIn("choices", resp)
        self.assertEqual(len(resp["choices"]), 1)
        self.assertIn("message", resp["choices"][0])
        self.assertIn("role", resp["choices"][0]["message"])
        self.assertIn("content", resp["choices"][0]["message"])
        self.assertIn("finish_reason", resp["choices"][0])
        self.assertIn("usage", resp)


if __name__ == "__main__":
    unittest.main()
