import os
import tempfile
import time
import unittest

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

from leptonai import Photon
from leptonai.client import Client, local

from utils import random_name, photon_run_local_server


class InitwithWarmUpCall(Photon):
    def init(self):
        # Since calling any handler function will trigger an init call, we need to make sure
        # that we can actually do so inside init.
        self.sleep(seconds=0.1)

    @Photon.handler()
    def sleep(self, seconds: float) -> str:
        time.sleep(seconds)
        return "done"


class TestPhotonInitWithWarmUp(unittest.TestCase):
    def setUp(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle
            import sys

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

    def test_warmup_call_passes(self):
        name = random_name()
        ph = InitwithWarmUpCall(name=name)
        path = ph.save()

        proc, port = photon_run_local_server(path=path)

        client = Client(local(port=port))
        # Test if the client works
        self.assertEqual(client.sleep(seconds=0.1), "done")


if __name__ == "__main__":
    unittest.main()
