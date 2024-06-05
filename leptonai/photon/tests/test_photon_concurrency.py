"""
This file is used to test the concurrency of the photon module.

Specifically, the following are tested:
- For synchronous endpoints defined with @Photon.handler, they
  can be called concurrently.
- When the endpoints are being called, the photon server can
  still accept new connections.
- For asynchronous endpoints defined with @Photon.handler, we
  are not automatically making them parallel, but as long as
  the user is using async primitives (e.g. async with, await),
  they can be called concurrently.
"""

import asyncio
import concurrent.futures
import os
import tempfile
import threading
import time
import unittest

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

from leptonai import Photon
from leptonai.client import Client, local

from utils import random_name, photon_run_local_server, skip_if_macos


class SimplePhoton(Photon):
    handler_max_concurrency = 5

    @Photon.handler
    def return_time(self, seconds: float) -> float:
        time.sleep(seconds)
        return time.time()

    @Photon.handler
    def return_thread_id(self) -> int:
        # sleep for a small amount time to make sure that thread stays longer than map()
        # overhead.
        time.sleep(0.01)
        return threading.get_ident()


class SimpleAsyncPhoton(Photon):
    handler_max_concurrency = 5

    @Photon.handler
    async def return_time(self, seconds: float) -> float:
        """
        This is an async endpoint
        """
        await asyncio.sleep(seconds)
        return time.time()

    @Photon.handler
    async def return_time_with_sync_sleep(self, seconds: float) -> float:
        time.sleep(seconds)
        return time.time()


@skip_if_macos
class TestPhotonConcurrencyBasic(unittest.TestCase):
    def setUp(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle
            import sys

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

    def test_simple_photon(self):
        name = random_name()
        ph = SimplePhoton(name=name)
        path = ph.save()

        proc, port = photon_run_local_server(path=path)

        client = Client(local(port=port))
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            trials = [0.1] * 5
            start = time.time()
            return_times = list(
                executor.map(lambda v: client.return_time(seconds=v), trials)
            )
            # assert that all tasks are executed in parallel
            self.assertTrue(all([t - start < 0.15 for t in return_times]))

            trials = [0.1] * 10
            start = time.time()
            return_times = list(
                executor.map(lambda v: client.return_time(seconds=v), trials)
            )
            # it should be taking a total of ~ 0.2 seconds, with the first 5 finishing in 0.15 seconds.
            self.assertEqual(sum([t - start < 0.15 for t in return_times]), 5)

            trials = [1] + [0.1] * 40
            start = time.time()
            return_times = list(
                executor.map(lambda v: client.return_time(seconds=v), trials)
            )
            # All the "waiting for 0.1s" jobs should finish by the first second.
            self.assertTrue(all([t - start < 1.15 for t in return_times]))

            trials = range(5)
            thread_ids = list(executor.map(lambda v: client.return_thread_id(), trials))
            # the thread ids should be different
            self.assertEqual(len(set(thread_ids)), 5)

        proc.kill()

    def test_simple_async_photon(self):
        name = random_name()
        ph = SimpleAsyncPhoton(name=name)
        path = ph.save()

        proc, port = photon_run_local_server(path=path)

        client = Client(local(port=port))
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            trials = [0.1] * 5
            start = time.time()
            return_times = list(
                executor.map(lambda v: client.return_time(seconds=v), trials)
            )
            # assert that all tasks are executed in parallel
            self.assertTrue(all([t - start < 0.15 for t in return_times]))

            trials = [0.1] * 10
            start = time.time()
            return_times = list(
                executor.map(lambda v: client.return_time(seconds=v), trials)
            )
            # it should be taking a total of ~ 0.2 seconds, with the first 5 finishing in 0.15 seconds.
            self.assertEqual(sum([t - start < 0.15 for t in return_times]), 5)

            trials = [1] + [0.1] * 40
            start = time.time()
            return_times = list(
                executor.map(lambda v: client.return_time(seconds=v), trials)
            )
            # All the "waiting for 0.1s" jobs should finish by the first second.
            self.assertTrue(all([t - start < 1.15 for t in return_times]))

            # But, when using return_time_with_sync_sleep, it should be blocking
            trials = [0.1] * 5
            start = time.time()
            return_times = list(
                executor.map(
                    lambda v: client.return_time_with_sync_sleep(seconds=v), trials
                )
            )
            self.assertGreaterEqual(max([t - start for t in return_times]), 0.5)


if __name__ == "__main__":
    unittest.main()
