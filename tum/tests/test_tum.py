import unittest

import torch

import tum


class TestTum(unittest.TestCase):
    def test_tum_enable(self):
        tum.enable()
        self.assertTrue(tum.enabled)
        tum.enable()

    def test_tum_allocate(self):
        tum.enable()
        torch.randn(100, 100, device="cuda")

    def test_prefetch(self):
        tum.enable()
        for _ in range(10):
            torch.randn(100, 100, device="cuda")
        tum.prefetch()

    def test_metadata(self):
        # TODO: Currently TUM doesn't cache gpu allocations like torch
        # native gpu allocator, which may result in performance
        # regression. Need to run benchmarks to verify and see if we
        # need to do caching as well.
        tum.enable()
        metadata = tum.metadata()
        x = torch.randn(100, 100, device="cuda")
        self.assertEqual(len(tum.metadata()), len(metadata) + 1)
        del x
        self.assertEqual(len(tum.metadata()), len(metadata))


if __name__ == "__main__":
    unittest.main()
