import multiprocessing
import time
from typing import Any
import unittest

import numpy as np

try:
    import torch
except ImportError:
    has_torch = False
else:
    has_torch = True

from leptonai.client import Client
from leptonai.photon.types import (
    is_pickled,
    lepton_pickle,
    lepton_unpickle,
    LeptonPickled,
)
from leptonai.photon import Photon, handler

from utils import find_free_port


class PicklePhoton(Photon):
    @handler("pickle")
    def pickle(self, obj: Any) -> LeptonPickled:
        return lepton_pickle(obj)

    @handler("pickle_compressed")
    def pickle_compressed(self, obj: Any) -> LeptonPickled:
        return lepton_pickle(obj, compression=1)

    @handler("unpickle_and_pickle")
    def unpickle_and_pickle(self, obj: LeptonPickled) -> LeptonPickled:
        return lepton_pickle(lepton_unpickle(obj))


def pickle_photon_wrapper(port):
    photon = PicklePhoton()
    photon.launch(port=port)


objects_to_test = [
    [1, 2, 3],
    lepton_pickle([1, 2, 3]),  # one shouldn't double-pickle stuff but we'll still test.
    {"key": "value"},
    {"key": [1, 2, 3]},
    [1, "2", 3.0, {"four": 4}],
]


class TestPickle(unittest.TestCase):
    def test_is_pickled(self):
        self.assertTrue(is_pickled(lepton_pickle([1, 2, 3])))
        self.assertFalse(is_pickled({}))
        self.assertFalse(is_pickled({"type": "not_pickled"}))
        # Really, one should not double-pickle stuff, but it is still a valid pickle
        self.assertTrue(is_pickled(lepton_pickle(lepton_pickle([1, 2, 3]))))

    def test_pickle(self):
        for obj in objects_to_test:
            self.assertTrue(is_pickled(lepton_pickle(obj)))
            self.assertEqual(lepton_unpickle(lepton_pickle(obj)), obj)

    def test_pickle_compressed(self):
        for obj in objects_to_test:
            self.assertTrue(is_pickled(lepton_pickle(obj, compression=1)))
            self.assertEqual(lepton_unpickle(lepton_pickle(obj, compression=1)), obj)

    def test_pickle_size_comparison(self):
        obj = ([1] * 1000,)
        last_size = len(lepton_pickle(obj, compression=0)["content"])
        for i in range(1, 10):
            size = len(lepton_pickle(obj, compression=i)["content"])
            self.assertLessEqual(size, last_size)
            last_size = size

    def test_pickle_numpy(self):
        a = np.random.rand(10, 10)
        self.assertEqual(lepton_unpickle(lepton_pickle(a)).all(), a.all())

    @unittest.skipIf(not has_torch, "torch is not installed")
    def test_pickle_torch(self):
        a = torch.rand(10, 10)
        self.assertEqual(lepton_unpickle(lepton_pickle(a)).all(), a.all())


class TestPickleWithPhoton(unittest.TestCase):
    def test_pickle_with_photon(self):
        port = find_free_port()
        proc = multiprocessing.Process(target=pickle_photon_wrapper, args=(port,))
        proc.start()
        time.sleep(2)
        url = f"http://localhost:{port}"
        c = Client(url)

        for obj in objects_to_test:
            res = c.pickle(obj=obj)
            self.assertTrue(is_pickled(res))
            self.assertEqual(lepton_unpickle(res), obj)

        # Test complex classes. Really, one should be very, very careful about
        # pickling and unpickling complex classes because any minor version mismatch
        # can cause the unpickling to fail. However, we'll still test it.

        # test numpy
        a = np.random.rand(10, 10)
        res = c.unpickle_and_pickle(obj=lepton_pickle(a))
        self.assertTrue(is_pickled(res))
        self.assertEqual(lepton_unpickle(res).all(), a.all())

        # test torch
        a = torch.rand(10, 10)
        res = c.unpickle_and_pickle(obj=lepton_pickle(a))
        self.assertTrue(is_pickled(res))
        self.assertEqual(lepton_unpickle(res).all(), a.all())

        proc.kill()


if __name__ == "__main__":
    unittest.main()
