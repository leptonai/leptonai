import os
import tempfile

# Set cache dir to a temp dir before importing anything from leptonai
tmpdir = tempfile.mkdtemp()
os.environ["LEPTON_CACHE_DIR"] = tmpdir

import unittest
import sys
import time
import threading

from loguru import logger
import requests

from leptonai.api.v0 import workspace as workspace_api
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

    def test_graceful_exit(self):
        class MyWorker(Worker):
            queue_name = TestWorker.queue_name
            kv_name = TestWorker.kv_name

            save_result = True

            # speed up test
            queue_empty_sleep_time = 1

            timeout_graceful_shutdown = 5
            incoming_traffic_grace_period = 10

            def on_task(self, task_id: str, x: int):
                time.sleep(2)
                logger.info(f"Got task {x}")
                return x * 2

        worker = MyWorker(name=random_name())
        path = worker.save()

        proc, port = photon_run_local_server(path=path)

        # create a task
        res = requests.post(f"http://localhost:{port}/task", json={"x": 2})
        self.assertEqual(res.status_code, 200, res.text)
        task_id = res.json()

        # wait for the task get picked up by the worker
        while True:
            res = requests.get(
                f"http://localhost:{port}/task", params={"task_id": task_id}
            )
            self.assertEqual(res.status_code, 200, res.text)
            if res.json()["status"] == "CREATED":
                logger.info("Waiting for worker to pick up the task")
                time.sleep(0.1)
            elif res.json()["status"] == "RUNNING":
                # send SIGTERM to the worker
                proc.terminate()
                break
            else:
                raise RuntimeError(f"Unexpected task status: {res.json()['status']}")
        # worker should still be able to finish the task
        time.sleep(3)
        res = requests.get(f"http://localhost:{port}/task", params={"task_id": task_id})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["result"], 4)

        # create another task (since incoming_traffic_grace_period is
        # 10s, server should still accept the task)
        res = requests.post(f"http://localhost:{port}/task", json={"x": 3})
        self.assertEqual(res.status_code, 200, res.text)
        task_id = res.json()

        # but worker should not pick up the task
        time.sleep(3)
        res = requests.get(f"http://localhost:{port}/task", params={"task_id": task_id})
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["status"], "CREATED")

    def test_worker_max_concurrency(self):
        class MyWorker(Worker):
            queue_name = TestWorker.queue_name
            kv_name = TestWorker.kv_name

            worker_max_concurrency = 2

            # speed up test
            queue_empty_sleep_time = 1

            def on_task(self, task_id: str, x: int) -> int:
                time.sleep(x)
                return x * 2

        worker = MyWorker(name=random_name())
        path = worker.save()

        proc, port = photon_run_local_server(path=path)

        start_time = time.time()

        # send 2 tasks in parallel
        def send():
            res = requests.post(f"http://localhost:{port}/task", json={"x": 5})
            self.assertEqual(res.status_code, 200, res.text)
            task_id = res.json()
            while True:
                res = requests.get(
                    f"http://localhost:{port}/task", params={"task_id": task_id}
                )
                self.assertEqual(res.status_code, 200, res.text)
                if res.json()["status"] == "SUCCESS":
                    break
                time.sleep(0.1)

        threads = [threading.Thread(target=send) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        end_time = time.time()
        # definitely less than 10s, since worker_max_concurrency is 2
        # should be around 5s, but considering the overhead of the test
        # it could be a bit more
        self.assertLess(end_time - start_time, 8)


if __name__ == "__main__":
    unittest.main()
