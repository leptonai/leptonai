import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.TemporaryDirectory()
os.environ["LEPTON_CACHE_DIR"] = tmpdir.name

import unittest

from loguru import logger

from leptonai import config
from leptonai import photon
from leptonai.util import check_photon_name

from utils import random_name

logger.info(f"Using cache dir: {config.CACHE_DIR}")


class TestPhotonSdk(unittest.TestCase):
    test_hf_model_id = "hf:sshleifer/tiny-gpt2"
    test_hf_model_id_revision = "5f91d94"

    def _test_create(self, model_id, revision=None):
        name = random_name()
        if revision is None:
            ph = photon.create(name=name, model=model_id)
        else:
            ph = photon.create(name=name, model=f"{model_id}@{revision}")
        self.assertEqual(ph._photon_name, name)
        if revision is not None:
            min_len = min(len(revision), len(ph.hf_revision))
            self.assertEqual(ph.hf_revision[:min_len], revision[:min_len])
        self.assertEqual(ph._photon_model, f"{model_id}@{ph.hf_revision}")
        self.assertEqual(ph.photon_type, "hf")

    def test_create(self):
        self._test_create(self.test_hf_model_id)

    def test_create_with_revision(self):
        self._test_create(
            self.test_hf_model_id, revision=self.test_hf_model_id_revision
        )

    def test_run(self):
        ph = photon.create(name="abcde", model=self.test_hf_model_id)
        ph.run("a cat")

    def test_save_and_load(self):
        ph = photon.create(name="abcdef", model=self.test_hf_model_id)
        revision = ph.hf_revision
        path = photon.save(ph)
        ph = photon.load(path)
        self.assertTrue(ph._photon_name == "abcdef")
        self.assertTrue(ph._photon_model == f"{self.test_hf_model_id}@{ph.hf_revision}")
        self.assertEqual(ph.hf_revision, revision)
        ph.run("a cat")

    def test_load_metadata(self):
        name = random_name()
        ph = photon.create(name=name, model=self.test_hf_model_id)
        path = photon.save(ph)
        metadata = photon.load_metadata(path)
        self.assertEqual(metadata["name"], name)

    def test_check_photon_name(self):
        for name in ["abcde", "abcde123", "abcde-123", "a" * 32]:
            check_photon_name(name)
        for name in ["abc 123", "abcde_123", "abcde-123_456", "abcde-", "a" * 33]:
            with self.assertRaisesRegex(ValueError, "Invalid Photon name"):
                check_photon_name(name)


if __name__ == "__main__":
    unittest.main()
