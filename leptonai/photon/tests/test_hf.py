import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest

from leptonai.photon import create, load_metadata
from utils import random_name


class TestHF(unittest.TestCase):
    def test_photon_file_metadata(self):
        name = random_name()
        model = "hf:sshleifer/tiny-gpt2@5f91d94"
        ph = create(name, model)
        path = ph.save()
        metadata = load_metadata(path)
        self.assertEqual(metadata["name"], name)
        self.assertTrue(metadata["model"].startswith(model))
        self.assertTrue("image" in metadata)
        self.assertTrue("args" in metadata)
        self.assertTrue("task" in metadata)
        self.assertTrue("openapi_schema" in metadata)
        self.assertTrue("/run" in metadata["openapi_schema"]["paths"])
        self.assertTrue("py_obj" not in metadata)
        self.assertEqual(len(metadata.get("requirement_dependency")), 1)

    def test_hf_photon_local_run(self):
        model = "hf:sshleifer/tiny-gpt2@5f91d94"
        ph = create(random_name(), model)
        text_input = "Hello world"
        res = ph.run(text_input)
        self.assertTrue(isinstance(res, str))
        self.assertTrue(res.startswith(text_input))

        batched_res = ph.run([text_input, text_input])
        self.assertTrue(isinstance(batched_res, list))
        self.assertEqual(len(batched_res), 2)
        self.assertTrue(batched_res[0].startswith(text_input))

    def test_hf_photon_extra_dependency(self):
        # We know that this one contains "flair"
        model = "hf:philschmid/flair-ner-english-ontonotes-large"
        ph = create(random_name(), model)
        self.assertTrue(
            any("flair" in dep for dep in ph._requirement_dependency),
            str(ph._requirement_dependency),
        )
        # Also, we check that if a repo has no requirements.txt, things still
        # work and hf:sshleifer/tiny-gpt2 should only have the default ctransformers dep.
        model = "hf:sshleifer/tiny-gpt2"
        ph = create(random_name(), model)
        self.assertEqual(ph._requirement_dependency, ["ctransformers"])


if __name__ == "__main__":
    unittest.main()
