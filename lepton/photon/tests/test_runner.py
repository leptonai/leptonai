import os
import tempfile

# Set cache dir to a temp dir before importing anything from lepton
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import json
from textwrap import dedent
import sys
import unittest
import zipfile

from loguru import logger
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


class CustomRunnerWithCustomDeps(Runner):
    requirement_dependency = ["torch"]

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
        proc.kill()
        self.assertEqual(res.status_code, 200)

    def test_runner_cli(self):
        with tempfile.NamedTemporaryFile(suffix=".py") as f:
            f.write(
                dedent(
                    """
from lepton.photon.runner import RunnerPhoton as Runner, handler


class Counter(Runner):
    def init(self):
        self.counter = 0

    @handler("add")
    def add(self, x: int) -> int:
        self.counter += x
        return self.counter

    @handler("sub")
    def sub(self, x: int) -> int:
        self.counter -= x
        return self.counter
"""
                ).encode("utf-8")
            )
            f.flush()
            proc, port = photon_run_server(name="counter", model=f"py:{f.name}:Counter")
            res = requests.post(
                f"http://127.0.0.1:{port}/add",
                json={"x": 1},
            )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), 1)

            res = requests.post(
                f"http://127.0.0.1:{port}/add",
                json={"x": 1},
            )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), 2)

            res = requests.post(
                f"http://127.0.0.1:{port}/sub",
                json={"x": 2},
            )
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json(), 0)
            proc.kill()

    def test_photon_file_metadata(self):
        name = random_name()
        runner = CustomRunner(name=name)
        path = runner.save()
        with zipfile.ZipFile(path, "r") as photon_file:
            with photon_file.open("metadata.json") as metadata_file:
                metadata = json.load(metadata_file)
        self.assertEqual(metadata["name"], name)
        self.assertEqual(metadata["model"], "CustomRunner")
        self.assertTrue("image" in metadata)
        self.assertTrue("args" in metadata)
        self.assertGreater(len(metadata.get("requirement_dependency")), 0)

    def test_custom_requirement_dependency(self):
        name = random_name()
        runner = CustomRunnerWithCustomDeps(name=name)
        path = runner.save()
        with zipfile.ZipFile(path, "r") as photon_file:
            with photon_file.open("metadata.json") as metadata_file:
                metadata = json.load(metadata_file)
        self.assertEqual(
            metadata["requirement_dependency"],
            CustomRunnerWithCustomDeps.requirement_dependency,
        )

    def test_metrics(self):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

        name = random_name()
        runner = CustomRunner(name=name)
        path = runner.save()

        proc, port = photon_run_server(path=path)

        for x in range(5):
            res = requests.post(
                f"http://127.0.0.1:{port}/some_path",
                json={"x": float(x)},
            )
            self.assertEqual(res.status_code, 200)
        res = requests.get(f"http://127.0.0.1:{port}/metrics")
        self.assertEqual(res.status_code, 200)
        self.assertRegex(
            res.text, r'http_request_duration_seconds_count{handler="/some_path"}'
        )
        proc.kill()


if __name__ == "__main__":
    unittest.main()
