import asyncio
import os
import tempfile
import time

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest
from leptonai.photon.batcher import batch
from utils import async_test


class TestBatcher(unittest.TestCase):
    @async_test
    async def test_batch_sync_func(self):
        @batch(max_batch_size=2, max_wait_time=0.001)
        def func(vals):
            return [v * 2 for v in vals]

        res = await asyncio.gather(func(1), func(2), func(3))
        self.assertEqual(res, [2, 4, 6])

    @async_test
    async def test_batch_async_func(self):
        @batch(max_batch_size=2, max_wait_time=0.001)
        async def func(vals):
            return [v * 2 for v in vals]

        res = await asyncio.gather(func(1), func(2), func(3))
        self.assertEqual(res, [2, 4, 6])

    @async_test
    async def test_preserve_attr(self):
        # sync version
        def func(vals):
            return [v * 2 for v in vals]

        batch_func = batch(max_batch_size=2, max_wait_time=0.001)(func)
        for attr in ["__name__", "__annotations__", "__qualname__", "__module__"]:
            self.assertEqual(getattr(func, attr), getattr(batch_func, attr))

        # async version
        async def func(vals):
            return [v * 2 for v in vals]

        batch_func = batch(max_batch_size=2, max_wait_time=0.001)(func)
        for attr in ["__name__", "__annotations__", "__qualname__", "__module__"]:
            self.assertEqual(getattr(func, attr), getattr(batch_func, attr))

    @async_test
    async def test_batch_max_batch_size(self):
        @batch(max_batch_size=2, max_wait_time=0.001)
        def func(vals):
            return [len(vals) + v for v in vals]

        res = await asyncio.gather(func(1), func(2), func(3))
        self.assertEqual(res, [3, 4, 4])

    @async_test
    async def test_batch_max_wait_time(self):
        @batch(max_batch_size=4, max_wait_time=1)
        def func(vals):
            return vals

        start = time.time()
        res = await asyncio.gather(func(1), func(2), func(3))
        self.assertEqual(res, [1, 2, 3])
        end = time.time()
        self.assertGreaterEqual(end - start, 0.9)


if __name__ == "__main__":
    unittest.main()
