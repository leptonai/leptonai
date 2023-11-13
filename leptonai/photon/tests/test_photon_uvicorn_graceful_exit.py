import os
import tempfile
import time
import unittest

import httpx

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

from leptonai import Photon
from leptonai.client import Client, local

from utils import random_name, photon_run_local_server


class IncomingTraffic(Photon):
    incoming_traffic_grace_period = 4

    @Photon.handler
    def run(self, sleep: int) -> str:
        time.sleep(sleep)
        return "done"


class TestPhotonConcurrencyBasic(unittest.TestCase):
    def setUp(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle
            import sys

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

    def test_graceful_exit(self):
        name = random_name()
        ph = IncomingTraffic(name=name)
        path = ph.save()

        proc, port = photon_run_local_server(path=path)

        client = Client(local(port=port))
        # Test if the client works
        self.assertEqual(client.run(sleep=0), "done")
        # send a terminate request to the process
        proc.terminate()
        # immediately, we should be able to still send a request
        self.assertEqual(client.run(sleep=1), "done")
        time.sleep(1)
        self.assertEqual(client.run(sleep=1), "done")
        time.sleep(2)  # should be longer than 4 seconds total
        # After the grace period, the server should not be able to accept new connections
        with self.assertRaises(httpx.ConnectError):
            client.run(sleep=0)


if __name__ == "__main__":
    unittest.main()
