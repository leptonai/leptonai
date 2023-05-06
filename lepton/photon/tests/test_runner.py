import os
import tempfile

# Set cache dir to a temp dir before importing anything from lepton
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import sys
import unittest

import requests
import torch

import lepton
from lepton.photon import RunnerPhoton as Runner


from utils import random_name, photon_run_server


class CustomRunner(Runner):
    def init(self):
        self.nn = torch.nn.Linear(1, 1)

    @Runner.handler("some_path")
    def run(self, x: float) -> float:
        return self.nn(torch.tensor(x).reshape(1, 1)).item()


class TestRunner(unittest.TestCase):
    def test_run(self):
        name = random_name()
        runner = CustomRunner(name=name)
        x = 2.0
        y1 = runner.run(x)

        xtensor = torch.tensor(x).reshape(1, 1)
        y2 = runner.nn(xtensor).item()
        self.assertEqual(y1, y2)

    def test_save_load(self):
        name = random_name()
        runner = CustomRunner(name=name)
        x = 2.0
        y1 = runner.run(x)

        path = runner.save()

        runner = lepton.photon.load(path)
        y2 = runner.run(x)
        self.assertEqual(y1, y2)

    def test_run_server(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

        name = random_name()
        runner = CustomRunner(name=name)
        path = runner.save()

        proc, port = photon_run_server(path=path)

        x = 2.0
        res = requests.post(
            f"http://localhost:{port}/some_path",
            json={"x": x},
        )
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
