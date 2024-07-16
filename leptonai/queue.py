"""
Lepton's queue API is a simple message queue. It is useful for sending messages between
deployments. For example, you can use the KV API and the queue API to build a distributed
task manager.
"""

import asyncio
from queue import Empty
import time
from typing import Optional, Union

from loguru import logger

from leptonai.api.v0 import queue as queue_api
from leptonai.api.v0.connection import Connection
from leptonai.api.v0 import workspace as workspace_api

# If not ready, wait for this amount of seconds before checking again.
_lepton_readiness_wait_time_ = 10
# Timeout limit.
_lepton_readiness_timeout_ = 60 * 5  # 5 minutes

# max queue value lengths: 256KB for value.
_lepton_max_value_length_ = 256 * 1024


class Queue(object):
    """
    Queue. doc tbd.
    """

    @staticmethod
    def create_queue(name: str, conn: Optional[Connection] = None) -> "Queue":
        """
        Create a queue.
        """
        queue_instance = Queue(
            name,
            create_if_not_exists=True,
            error_if_exists=True,
            conn=conn,
        )
        return queue_instance

    @staticmethod
    def get_queue(name: str, conn: Optional[Connection] = None) -> "Queue":
        """
        Get an existing queue.
        """
        kv_instance = Queue(name, create_if_not_exists=False, conn=conn)
        return kv_instance

    @staticmethod
    def delete_queue(name: Union["Queue", str], conn: Optional[Connection] = None):
        """
        Delete a queue.
        """
        conn = conn if conn else workspace_api.current_connection()
        if isinstance(name, Queue):
            name = name._queue
        res = queue_api.delete_queue(conn, name)
        if not res.ok:
            raise RuntimeError(
                f"Failed to delete queue {name}. Error:"
                f" {res.status_code} {res.content}."
            )

    @staticmethod
    def list_queue(conn: Optional[Connection] = None):
        """
        List queues in the current workspace.
        """
        conn = conn if conn else workspace_api.current_connection()
        res = queue_api.list_queue(conn)
        if not res.ok:
            raise RuntimeError(
                f"Failed to list queues. Error: {res.status_code} {res.content}."
            )
        else:
            return [s["name"] for s in res.json()]

    def __init__(
        self,
        name: str,
        create_if_not_exists: bool = False,
        error_if_exists: bool = False,
        wait_for_creation: bool = True,
        conn: Optional[Connection] = None,
    ):
        """
        Initializes a queue.

        :param str name: the name of the queue
        :param bool create_if_not_exists: if True, create the queue if it does not exist
        :param bool error_if_exists: if True, raise an error if the queue already exists
        :param wait_for_creation: if True, wait for the queue to be ready
        :param Connection conn: the connection to use. If None, use the default workspace connection.
        """
        self._conn = conn if conn else workspace_api.current_connection()
        existing_queues = Queue.list_queue(self._conn)
        if name in existing_queues:
            if error_if_exists:
                raise ValueError(
                    f"queue {name} already exists, and you have specified"
                    " error_if_exists=True."
                )
            else:
                self._queue = name
        else:
            if create_if_not_exists:
                res = queue_api.create_queue(self._conn, name)
                if not res.ok:
                    raise RuntimeError(
                        f"Failed to create queue {name}. Error:"
                        f" {res.status_code} {res.content}."
                    )
                else:
                    self._queue = name
                if wait_for_creation:
                    # wait for the queue to be ready
                    start = time.time()
                    while time.time() - start < _lepton_readiness_timeout_:
                        if self.ready():
                            break
                        logger.trace(f"Queue {name} is not ready yet. Waiting...")
                        time.sleep(_lepton_readiness_wait_time_)
                    else:
                        raise RuntimeError(
                            f"Queue {name} is not ready after"
                            f" {time.time() - start} seconds."
                        )
            else:
                raise ValueError(
                    f"Queue {name} does not exist, and you have specified"
                    " create_if_not_exists=False."
                )

    def ready(self) -> bool:
        existing_queues = Queue.list_queue(self._conn)
        return self._queue in existing_queues

    async def async_wait(self):
        """
        Returns if the queue is ready to use, but wait for the queue to be ready asynchronously.
        """
        start = time.time()
        while time.time() - start < _lepton_readiness_timeout_:
            if self.ready():
                break
            logger.trace(f"Queue {self._queue} is not ready yet. Waiting...")
            await asyncio.sleep(_lepton_readiness_wait_time_)
        else:
            raise RuntimeError(
                f"Queue {self._queue} is not ready after {time.time() - start} seconds."
            )

    def length(self) -> int:
        """
        Get the length of the queue.
        """
        res = queue_api.length(self._conn, self._queue)
        if not res.ok:
            raise RuntimeError(
                f"Failed to get length of queue {self._queue}. Error:"
                f" {res.status_code} {res.content}."
            )
        else:
            return res.json()["length"]

    def receive(self) -> str:
        """
        Receive a message from the queue. Raises Empty if the queue is empty.
        """
        res = queue_api.receive(self._conn, self._queue)
        if not res.ok:
            raise RuntimeError(
                f"Failed to get message from queue {self._queue}. Error:"
                f" {res.status_code} {res.content}."
            )
        else:
            try:
                content = res.json()
            except Exception:
                raise RuntimeError(
                    f"Failed to parse response from queue {self._queue}. Error:"
                    f" {res.status_code} {res.content}."
                )
            if len(content) == 0:
                raise Empty
            else:
                if len(content) > 1:
                    raise RuntimeError(
                        "You hit a bug in the queue api. Right now we only support one"
                        " message at a time."
                    )
                return content[0]["message"]

    def send(self, message: str):
        """
        Send a message to the queue.

        Note that Lepton queue carries out deduplication: if you send the same message
        twice, the second message will be discarded. This is useful for distributed fault
        tolerance. The deduplication is based on the content of the message, and the dedup
        time window is around 5 minutes.
        """
        if len(message) > _lepton_max_value_length_:
            raise ValueError(
                f"Value length {len(message)} exceeds the maximum allowed length"
                f" {_lepton_max_value_length_}."
            )
        res = queue_api.send(self._conn, self._queue, message)
        if not res.ok:
            raise RuntimeError(
                f"Failed to put message to queue {self._queue}. Error:"
                f" {res.status_code} {res.content}."
            )
