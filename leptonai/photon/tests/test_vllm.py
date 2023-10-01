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
        self.assertEqual(len(metadata.get("requirement_dependency")), 2)

    def test_run_vllm_photon(self):
        model = "vllm:gpt2"
        proc, port = photon_run_local_server(name=random_name(), model=model)
        client = Client(f"http://127.0.0.1:{port}")
        resp = client.api.v1.completions(
            model="gpt2",
            prompt="Hello world",
            max_tokens=10,
        )
        print(resp)


if __name__ == "__main__":
    unittest.main()
