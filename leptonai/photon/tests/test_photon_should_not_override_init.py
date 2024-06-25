import os
import tempfile
import time
import threading
import unittest

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

from leptonai import Photon


class InitOverridden(Photon):
    def __init__(self):
        pass


class InitOverriddenButCalledBase(Photon):
    def __init__(self, name=None, model=None):
        super().__init__(name=name, model=model)


class TestPhotonShouldNotOverrideInit(unittest.TestCase):
    def setUp(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle
            import sys

            cloudpickle.register_pickle_by_value(sys.modules[__name__])
        self.e = None

    def _test_init_should_work(self):
        ph = InitOverriddenButCalledBase()
        try:
            ph.launch()
        except Exception as e:
            self.e = e

    def test_init(self):
        ph = InitOverridden()
        with self.assertRaises(RuntimeError):
            ph.launch()

        t = threading.Thread(target=self._test_init_should_work)
        t.setDaemon(True)
        t.start()
        time.sleep(0.1)
        self.assertIsNone(self.e)
        t.join(timeout=0)


if __name__ == "__main__":
    unittest.main()
