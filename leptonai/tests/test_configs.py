from importlib import reload
import os
import torch
import unittest


class TestConfig(unittest.TestCase):
    def test_is_rocm_flag(self):
        from leptonai import config

        # Since we cannot really control the underlying hardware, we try our best
        # to test the flag.
        if torch.cuda.is_available():
            self.assertEqual(config._is_rocm(), (torch.version.hip is not None))
        os.environ["LEPTON_BASE_IMAGE_FORCE_ROCM"] = "true"
        reload(config)
        self.assertTrue(config._is_rocm())
        self.assertIn("photon-rocm-py", config.BASE_IMAGE)
        self.assertNotIn("photon-py", config.BASE_IMAGE)

        os.environ["LEPTON_BASE_IMAGE_FORCE_ROCM"] = "false"
        reload(config)
        self.assertFalse(config._is_rocm())
        self.assertNotIn("photon-rocm-py", config.BASE_IMAGE)
        self.assertIn("photon-py", config.BASE_IMAGE)


if __name__ == "__main__":
    unittest.main()
