import concurrent
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


class CustomPhotonWithGracefulShutdown(Photon):
    timeout_graceful_shutdown = 5
    incoming_traffic_grace_period = 0

    @Photon.handler()
    def sleep(self, seconds: int) -> str:
        time.sleep(seconds)
        return "done"


class CustomPhotonWithGracefulIncomingTraffic(Photon):
    incoming_traffic_grace_period = 4

    @Photon.handler
    def run(self, sleep: int) -> str:
        time.sleep(sleep)
        return "done"


class TestPhotonGraceful(unittest.TestCase):
    def setUp(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle
            import sys

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

    def test_graceful_incoming_graffic(self):
        name = random_name()
        ph = CustomPhotonWithGracefulIncomingTraffic(name=name)
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

    def test_graceful_shutdown(self):
        name = random_name()
        ph = CustomPhotonWithGracefulShutdown(name=name)
        path = ph.save()

        proc, port = photon_run_local_server(path=path)

        def call_sleep(seconds: int):
            c = Client(Client.local(port=port))
            return c.sleep(seconds=seconds)

        self.assertEqual(call_sleep(1), "done")

        thread_1 = concurrent.futures.ThreadPoolExecutor().submit(call_sleep, 2)
        # ensure thread_1 is submitted and before thread_2
        time.sleep(0.1)
        thread_2 = concurrent.futures.ThreadPoolExecutor().submit(call_sleep, 10)
        # ensure thread_2 is submitted
        time.sleep(0.1)
        proc.terminate()
        # Tests that thread 1 can finish successfully due to the graceful shutdown setup.
        self.assertEqual(thread_1.result(), "done")
        # Tests that thread_2 won't be able to finish, and throws a httpx.HTTPStatusError.
        with self.assertRaises(httpx.HTTPStatusError):
            thread_2.result()


if __name__ == "__main__":
    unittest.main()
