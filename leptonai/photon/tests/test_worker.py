import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest
import sys
import time

from loguru import logger
import requests

from leptonai.api import workspace as workspace_api
from leptonai.photon import Worker
from leptonai.kv import KV
from leptonai.queue import Queue
from utils import random_name, photon_run_local_server


@unittest.skipIf(
    workspace_api.WorkspaceInfoLocalRecord.get_current_workspace_id() is None,
    "No login info. Skipping test.",
)
class TestWorker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # pytest imports test files as top-level module which becomes
        # unavailable in server process
        if "PYTEST_CURRENT_TEST" in os.environ:
            import cloudpickle

            cloudpickle.register_pickle_by_value(sys.modules[__name__])

        cls.kv_name = random_name()
        logger.info(f"Creating KV {cls.kv_name}")
        KV(cls.kv_name, create_if_not_exists=True)
        logger.info(f"KV {cls.kv_name} created")

        cls.queue_name = random_name()
        logger.info(f"Creating Queue {cls.queue_name}")
        Queue(cls.queue_name, create_if_not_exists=True)
        logger.info(f"Queue {cls.queue_name} created")

    @classmethod
    def tearDownClass(cls):
        KV.delete_kv(cls.kv_name)
        Queue.delete_queue(cls.queue_name)

    def test_worker(self):
        class MyWorker(Worker):
            queue_name = TestWorker.queue_name
            kv_name = TestWorker.kv_name

            # speed up test
            queue_empty_sleep_time = 1

            def on_task(self, task_id: str, x: int):
                time.sleep(2)
                logger.info(f"Got task {x}")
                return x * 2

        worker = MyWorker(name=random_name())
        path = worker.save()

        proc, port = photon_run_local_server(path=path)
        res = requests.post(f"http://localhost:{port}/task", json={"x": 1})
        self.assertEqual(res.status_code, 200, res.text)
        task_id = res.json()
        self.assertTrue(isinstance(task_id, str))
        logger.info(f"Got task id {task_id}")

        time.sleep(3)
        res = requests.get(f"http://localhost:{port}/task", params={"task_id": task_id})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertIn("status", res.json())
        self.assertIn(res.json()["status"], ["RUNNING", "SUCCESS"])
        self.assertIn("created_at", res.json())
        self.assertIn("started_at", res.json())
        if res.json()["status"] == "RUNNING":
            time.sleep(2)
            self.assertIn("finished_at", res.json())


if __name__ == "__main__":
    unittest.main()
