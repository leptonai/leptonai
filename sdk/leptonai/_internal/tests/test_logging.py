import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest

from leptonai._internal.logging import log as internal_log
from leptonai._internal.logging import _LOGFILE_BASE, enable, disable


class TestInternalLog(unittest.TestCase):
    def setUp(self):
        os.environ["LEPTON_ENABLE_INTERNAL_LOG"] = "1"
        enable()

    def tearDown(self):
        disable()
        del os.environ["LEPTON_ENABLE_INTERNAL_LOG"]

    def test_log(self):
        msg = "some random message"
        internal_log(msg)
        self.assertTrue(os.path.exists(_LOGFILE_BASE))
        with open(_LOGFILE_BASE, "r") as f:
            self.assertIn(msg, f.read())


if __name__ == "__main__":
    unittest.main()
