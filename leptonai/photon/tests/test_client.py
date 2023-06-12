import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest

from leptonai import Client
from utils import random_name, photon_run_server


class TestClient(unittest.TestCase):
    def test_client(self):
        # launch server
        name = random_name()
        proc, port = photon_run_server(name=name, model="hf:gpt2")
        url = f"http://localhost:{port}"

        client = Client(url)
        inputs = "hello world"
        res = client.run(inputs=inputs)
        self.assertTrue(isinstance(res, str))
        self.assertTrue(res.startswith(inputs))
        res = client.run(inputs="hello world", do_sample=True, max_length=10)
        self.assertTrue(isinstance(res, str))
        self.assertTrue(res.startswith(inputs))
        proc.kill()


if __name__ == "__main__":
    unittest.main()
