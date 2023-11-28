import asyncio
import os
import tempfile
import time
import unittest

import cloudpickle

from loguru import logger

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

from leptonai import Photon


class TestCloudPickle(unittest.TestCase):
    def setUp(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle
            import sys

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

    def test_cloudpickle_can_pickle(self):
        class SleepPhoton(Photon):
            @Photon.handler
            def sleep(self, seconds: int) -> float:
                start = time.time()
                time.sleep(seconds)
                end = time.time()
                return end - start

            @Photon.handler
            async def async_sleep(self, seconds: int) -> float:
                from loguru import logger

                try:
                    start = time.time()
                    await asyncio.sleep(seconds)
                    end = time.time()
                    return end - start
                except asyncio.CancelledError as e:
                    logger.info(f"async sleep cancelled due to {e}")
                    return -1

        ph = SleepPhoton()
        ph.save()


if __name__ == "__main__":
    unittest.main()
