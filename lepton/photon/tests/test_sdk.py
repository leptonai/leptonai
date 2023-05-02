import os
import tempfile

# Set cache dir to a temp dir before importing anything from lepton
tmpdir = tempfile.TemporaryDirectory()
os.environ["LEPTON_CACHE_DIR"] = tmpdir.name

import unittest

from loguru import logger
from transformers import AutoModel, pipeline

from lepton import config
from lepton import photon

from utils import random_name

logger.info(f"Using cache dir: {config.CACHE_DIR}")


class TestPhotonSdk(unittest.TestCase):
    test_hf_model_id = "hf:runwayml/stable-diffusion-v1-5"
    test_hf_model_id_revision = "39593d5"

    def _test_create(self, model_id, revision=None):
        name = random_name()
        if revision is None:
            ph = photon.create(name=name, model=model_id)
        else:
            ph = photon.create(name=name, model=f"{model_id}@{revision}")
        self.assertEqual(ph.name, name)
        if revision is not None:
            min_len = min(len(revision), len(ph.hf_revision))
            self.assertEqual(ph.hf_revision[:min_len], revision[:min_len])
        self.assertEqual(ph.model, f"{model_id}@{ph.hf_revision}")
        self.assertTrue(isinstance(ph, photon.HuggingfacePhoton))

    def test_create(self):
        self._test_create(self.test_hf_model_id)

    def test_create_with_revision(self):
        self._test_create(
            self.test_hf_model_id, revision=self.test_hf_model_id_revision
        )

    def test_run(self):
        ph = photon.create(name="abcde", model=self.test_hf_model_id)
        ph.run(prompt="a cat", num_inference_steps=2)

    def test_save_and_load(self):
        ph = photon.create(name="abcdef", model=self.test_hf_model_id)
        revision = ph.hf_revision
        path = photon.save(ph)
        ph = photon.load(path)
        self.assertTrue(ph.name == "abcdef")
        self.assertTrue(ph.model == f"{self.test_hf_model_id}@{ph.hf_revision}")
        self.assertEqual(ph.hf_revision, revision)
        ph.run(prompt="a cat", num_inference_steps=2)

    def test_create_from_transfomers_model(self):
        model_id = "gpt2"
        model = AutoModel.from_pretrained(model_id)

        ph = photon.create(name=model_id, model=model)

        self.assertTrue(ph.name == model_id)
        self.assertTrue(ph.model == f"hf:{model_id}@{ph.hf_revision}")
        ph.run("a cat")

    def test_create_from_transfomers_pipeline(self):
        model_id = "gpt2"
        pipe = pipeline(model=model_id)

        ph = photon.create(name=model_id, model=pipe)

        self.assertTrue(ph.name == model_id)
        self.assertTrue(ph.model == f"hf:{model_id}@{ph.hf_revision}")
        ph.run("a cat")


if __name__ == "__main__":
    unittest.main()
