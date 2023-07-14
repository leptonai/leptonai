import unittest

import numpy as np

try:
    import torch
except ImportError:
    has_torch = False
else:
    has_torch = True

from leptonai.photon.types import is_pickled, lepton_pickle, lepton_unpickle


class TestPickle(unittest.TestCase):
    def test_is_pickled(self):
        self.assertTrue(is_pickled(lepton_pickle([1, 2, 3])))
        self.assertFalse(is_pickled({}))
        self.assertFalse(is_pickled({"type": "not_pickled"}))
        # Really, one should not double-pickle stuff, but it is still a valid pickle
        self.assertTrue(is_pickled(lepton_pickle(lepton_pickle([1, 2, 3]))))

    def test_pickle(self):
        self.assertEqual(lepton_unpickle(lepton_pickle([1, 2, 3])), [1, 2, 3])
        self.assertEqual(
            lepton_unpickle(lepton_pickle({"key": "value"})), {"key": "value"}
        )
        self.assertEqual(
            lepton_unpickle(lepton_pickle({"key": [1, 2, 3]})), {"key": [1, 2, 3]}
        )
        self.assertEqual(lepton_unpickle(lepton_pickle((1, 2, 3))), (1, 2, 3))
        self.assertEqual(
            lepton_unpickle(lepton_pickle((1, "2", 3.0, {"four": 4}))),
            (1, "2", 3.0, {"four": 4}),
        )

    def test_pickle_numpy(self):
        a = np.random.rand(10, 10)
        self.assertEqual(lepton_unpickle(lepton_pickle(a)).all(), a.all())

    @unittest.skipIf(not has_torch, "torch is not installed")
    def test_pickle_torch(self):
        a = torch.rand(10, 10)
        self.assertEqual(lepton_unpickle(lepton_pickle(a)).all(), a.all())


if __name__ == "__main__":
    unittest.main()
