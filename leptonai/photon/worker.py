import asyncio
from abc import abstractmethod
import datetime
from enum import Enum
import json
import os
import threading
import time
from typing import Any, Dict, Optional
import uuid

import anyio
from loguru import logger

from .photon import Photon, HTTPException
from leptonai.api.v1.workspace_record import WorkspaceRecord
from leptonai.util import asyncfy_with_semaphore


class Status(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Worker(Photon):
    # The queue name and the KV name that the worker will use. The queue and the KV
    # will be created if they don't exist. Note that you are responsible for making
    # sure the uniqueness of queue and kv names. If they are left as None, the deployment
    # name will serve as the queue name and the kv name. When runnining the
    # deployment, make sure to set the LEPTON_WORKSPACE_TOKEN environment variable as the
    # workspace token. You can also do this by adding --include-workspace-token to the
    # lep photon run command to include the workspace token in the environment variables.
    queue_name: Optional[str] = None
    kv_name: Optional[str] = None

    # Whether to save the result of the task to the KV. If set to False, the result
    # of on_task will be simply ignored, and only the task state is saved to the KV.
    # In default, the result is saved to the KV.
    save_result: bool = True

    # The time to sleep when the queue is empty.
    queue_empty_sleep_time: int = 5
    # The time to sleep when worker max concurrency is reached.
    worker_max_concurrency_sleep_time: int = 5

    # The maximum number of concurrent tasks that the worker can
    # process. Default to 1 to avoid needing to deal with locks.
    worker_max_concurrency: int = 1

    # The tag used to identify the task id in the payload. In most cases, you should
    # not need to change this.
    LEPTON_TASK_ID_TAG = "_lepton_task_id"

    _loop_started = False

    def init(self):
        """
        Worker's own init function that starts the loop.

        If you build a derived Photon based on Worker, you can explicitly call
        super().init() to start the loop in the init function. Note that when the
        loop starts, the worker will start to process tasks, so any worker specific
        init (like loading models) should be done before calling super().init().

        If your class does not implement the init function, the Worker's init function
        will be called automatically.
        """
        # to avoid circular import
        from leptonai.kv import KV
        from leptonai.queue import Queue

        super().init()
        # Logs in to the workspace if not logged in yet.
        if not WorkspaceRecord.current():
            # Try to log in with the environmental variables.
            WorkspaceRecord.login_with_env()
        # Starts the loop.
        if not self._loop_started:
            self._loop_started = True
            # creates the queue.
            if self.queue_name is None:
                if os.environ.get("LEPTON_DEPLOYMENT_NAME") is None:
                    raise RuntimeError(
                        "queue_name is not set and LEPTON_DEPLOYMENT_NAME is not set"
                    )
                else:
                    self.queue_name = os.environ["LEPTON_DEPLOYMENT_NAME"]
            self._queue = Queue(
                self.queue_name, create_if_not_exists=True, wait_for_creation=True
            )
            # creates the kv.
            if self.kv_name is None:
                if os.environ.get("LEPTON_DEPLOYMENT_NAME") is None:
                    raise RuntimeError(
                        "kv_name is not set and LEPTON_DEPLOYMENT_NAME is not set"
                    )
                else:
                    self.kv_name = os.environ["LEPTON_DEPLOYMENT_NAME"]
            self._kv = KV(
                self.kv_name, create_if_not_exists=True, wait_for_creation=True
            )

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
        from leptonai.queue import Empty

        loop = asyncio.new_event_loop()
        # TODO: Is this the right way to start the loop?
        threading.Thread(target=loop.run_forever, daemon=True).start()

        pending_futures = set()

        last_message_received_at = None
        while True:
            if self._lepton_worker_thread_should_exit:
                logger.info("Received worker should exit signal, exiting")
                loop.stop()
                break

            if len(pending_futures) >= self.worker_max_concurrency:
                time.sleep(self.worker_max_concurrency_sleep_time)
                continue

            try:
                message = self._queue.receive()

                if last_message_received_at is not None:
                    time_since_last_message = (
                        datetime.datetime.utcnow() - last_message_received_at
                    ).total_seconds()
                    logger.info(
                        f"Received new message after {time_since_last_message} seconds"
                    )
                last_message_received_at = datetime.datetime.utcnow()

                payload = json.loads(message)
                task_id = payload.pop(self.LEPTON_TASK_ID_TAG)

                future = asyncio.run_coroutine_threadsafe(
                    self._on_task(task_id, **payload), loop
                )
                pending_futures.add(future)
                future.add_done_callback(pending_futures.remove)
            except Empty:
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
