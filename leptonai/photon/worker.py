import asyncio
from abc import abstractmethod
import datetime
from enum import Enum
import json
import threading
import time
from typing import Any, Dict
import uuid

import anyio
from loguru import logger

from .photon import Photon, HTTPException
from leptonai.queue import Queue, Empty
from leptonai.kv import KV
from leptonai.util import asyncfy_with_semaphore


class Status(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Worker(Photon):
    queue_name: str = None
    kv_name: str = None

    queue_empty_sleep_time: int = 5
    save_result: bool = False

    # The maximum number of concurrent tasks that the worker can
    # process. Default to 1 to avoid needing to deal with locks.
    worker_max_concurrency: int = 1

    LEPTON_TASK_ID_TAG = "_lepton_task_id"

    def init(self):
        super().init()

        if self.queue_name is None:
            raise RuntimeError("queue_name is not set")
        self._queue = Queue(
            self.queue_name, create_if_not_exists=False, wait_for_creation=True
        )
        if self.kv_name is None:
            raise RuntimeError("kv_name is not set")
        self._kv = KV(self.kv_name, create_if_not_exists=False, wait_for_creation=True)

        self._worker_semaphore = anyio.Semaphore(self.worker_max_concurrency)
        self._on_task_handler = asyncfy_with_semaphore(
            self.on_task, self._worker_semaphore
        )

        self._lepton_worker_thread_should_exit = False
        threading.Thread(target=self._worker_loop, daemon=True).start()

    def _handle_exit(self, *args, **kwargs) -> None:
        self._lepton_worker_thread_should_exit = True
        super()._handle_exit(*args, **kwargs)

    def _worker_loop(self):
        """Keep polling the queue for new tasks, and dispatch them to `on_task` (through `_on_task`)"""

        loop = asyncio.new_event_loop()

        while True:
            if self._lepton_worker_thread_should_exit:
                logger.info("Received worker should exit signal, exiting")
                break
            try:
                message = self._queue.receive()
                payload = json.loads(message)
                task_id = payload.pop(self.LEPTON_TASK_ID_TAG)
                loop.run_until_complete(self._on_task(task_id, **payload))
            except Empty:
                logger.info(
                    "Queue is empty, sleeping for"
                    f" {self.queue_empty_sleep_time} seconds"
                )
                time.sleep(self.queue_empty_sleep_time)
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")

    async def _on_task(self, task_id: str, **payload):
        """Do some accounting and error handling work, then dispatch the task to `on_task`"""

        logger.info(f"Received task {task_id}")

        task_json = json.loads(self._kv.get(task_id))
        task_json["status"] = Status.RUNNING
        task_json["started_at"] = datetime.datetime.utcnow().isoformat()
        self._kv.put(task_id, json.dumps(task_json))

        try:
            res = await self._on_task_handler(task_id=task_id, **payload)
        except Exception as e:
            logger.exception(f"Task {task_id} failed: {e}")
            task_json["status"] = Status.FAILED
        else:
            logger.info(f"Task {task_id} succeeded")
            task_json["status"] = Status.SUCCESS
            if self.save_result:
                task_json["result"] = res
        finally:
            task_json["finished_at"] = datetime.datetime.utcnow().isoformat()
            self._kv.put(task_id, json.dumps(task_json))

        logger.info(f"Task {task_id} finished")

    @abstractmethod
    def on_task(self, task_id: str, **payload):
        """The actual task handler, should be implemented by concrete Worker subclass"""
        raise NotImplementedError("Concrete Worker subclass should implement on_task")

    @Photon.handler(path="task", method="POST", use_raw_args=True)
    def task_post(self, payload: Dict[str, Any]):
        task_id = uuid.uuid4().hex

        logger.info(f"request: {payload}")

        payload[self.LEPTON_TASK_ID_TAG] = task_id
        self._queue.send(json.dumps(payload))

        task_json = {
            "status": Status.CREATED,
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
        self._kv.put(task_id, json.dumps(task_json))

        return task_id

    @Photon.handler(path="task", method="GET")
    def task_get(self, task_id: str):
        try:
            task_str = self._kv.get(task_id)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Task ({task_id}) not found")
        else:
            task_json = json.loads(task_str)
            return task_json
