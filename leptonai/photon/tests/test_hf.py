import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import json
import unittest
import zipfile

from leptonai.photon import create
from utils import random_name


class TestHF(unittest.TestCase):
    def test_photon_file_metadata(self):
        name = random_name()
        model = "hf:gpt2"
        runner = create(name, model)
        path = runner.save()
        with zipfile.ZipFile(path, "r") as photon_file:
            with photon_file.open("metadata.json") as metadata_file:
                metadata = json.load(metadata_file)
        self.assertEqual(metadata["name"], name)
        self.assertTrue(metadata["model"].startswith(model))
        self.assertTrue("image" in metadata)
        self.assertTrue("args" in metadata)
        self.assertTrue("task" in metadata)
        self.assertTrue("openapi_schema" in metadata)
        self.assertTrue("/run" in metadata["openapi_schema"]["paths"])
        self.assertTrue("py_obj" not in metadata)
        self.assertEqual(len(metadata.get("requirement_dependency")), 0)


if __name__ == "__main__":
    unittest.main()
