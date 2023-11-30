"""
Lepton's KV API is a simple key-value store. It is useful for storing small pieces of data
that are not directly related to a deployment, and can be accessed by multiple deployments.
For example, you can use the KV API and the Queue API to build a distributed task manager.
"""

import asyncio
import time
from typing import Optional, Union

from loguru import logger

from leptonai.api import kv as kv_api
from leptonai.api.connection import Connection
from leptonai.api import workspace as workspace_api


# Key to test the readiness of the KV.
_lepton_readiness_test_key_ = "_lepton_readiness_test_key_"
_lepton_readiness_test_value_ = "_lepton_readiness_test_value_"
# If not ready, wait for this amount of seconds before checking again.
_lepton_readiness_wait_time_ = 10
# Timeout limit.
_lepton_readiness_timeout_ = 60 * 5  # 5 minutes

# max key and value lengths: 256 bytes for key, and 256KB for value.
_lepton_max_key_length_ = 256
_lepton_max_value_length_ = 256 * 1024


class KV(object):
    """
    The Lepton Key-Value store. Every named KV can be considered the equivalent of a KV / table / collection,
    composed of keys as strings and values as bytes.

    To create a KV, use the following code:
    ```
    my_kv = KV("my_kv_name", create_if_not_exists=True)
    ```

    As a serverless KV service, creation may take some time. By default, the constructor will wait
    for it to be ready. If you do not want to wait, you can set `wait_for_creation=False`:
    ```
    my_kv = KV("my_kv_name", create_if_not_exists=True, wait_for_creation=False)
    # use my_kv.ready() to check if the KV is ready.
    is_ready: bool = my_kv.ready()
    # or, use my_kv.async_wait() to wait for the KV to be ready asynchronously.
    await my_kv.async_wait()
    ```

    When the KV is ready, you can use `my_kv.put(key, value)` to put a key-value pair, `my_kv.get(key)` to get the
    value of a key, and `my_kv.delete(key)` to delete a key-value pair. The key should be
    a valid python string and the value should be either a valid python string or bytes.
    """

    @staticmethod
    def create_kv(
        name: str, wait_for_creation: bool = True, conn: Optional[Connection] = None
    ) -> "KV":
        """
        Create a KV.
        """
        conn = conn if conn else workspace_api.current_connection()
        kv_instance = KV(
            name,
            create_if_not_exists=True,
            error_if_exists=True,
            wait_for_creation=wait_for_creation,
            conn=conn,
        )
        return kv_instance

    @staticmethod
    def get_kv(name: str, conn: Optional[Connection] = None) -> "KV":
        """
        Get an existing KV.
        """
        conn = conn if conn else workspace_api.current_connection()
        kv_instance = KV(name, create_if_not_exists=False, conn=conn)
        return kv_instance

    @staticmethod
    def delete_kv(name: Union["KV", str], conn: Optional[Connection] = None):
        """
        Delete a KV.
        """
        conn = conn if conn else workspace_api.current_connection()
        if isinstance(name, KV):
            name = name._kv
        res = kv_api.delete_kv(conn, name)
        if not res.ok:
            raise RuntimeError(
                f"Failed to delete KV {name}. Error: {res.status_code} {res.content}."
            )

    def __init__(
        self,
        name: str,
        create_if_not_exists: bool = False,
        error_if_exists: bool = False,
        wait_for_creation: bool = True,
        conn: Optional[Connection] = None,
    ):
        """
        Initializes a KV.

        :param str name: the name of the KV
        :param bool create_if_not_exists: if True, create the KV if it does not exist
        :param bool error_if_exists: if True, raise an error if the KV already exists
        :param bool wait_for_creation: if True, wait for the KV to be ready
        :param Connection conn: the connection to use. If None, use the default workspace connection.
        """
        self._conn = conn if conn else workspace_api.current_connection()
        res = kv_api.list_kv(self._conn)
        if not res.ok:
            raise RuntimeError(
                f"Failed to access KV server. Error: {res.status_code} {res.content}."
            )
        exitsting_kvs = [s["name"] for s in res.json()]
        if name in exitsting_kvs:
            if error_if_exists:
                raise ValueError(
                    f"KV {name} already exists, and you have specified"
                    " error_if_exists=True."
                )
            else:
                self._kv = name
        else:
            if create_if_not_exists:
                res = kv_api.create_kv(self._conn, name)
                if not res.ok:
                    raise RuntimeError(
                        f"Failed to create KV {name}. Error:"
                        f" {res.status_code} {res.content}."
                    )
                else:
                    self._kv = name
                if wait_for_creation:
                    start = time.time()
                    while (
                        not self.ready()
                        and time.time() - start < _lepton_readiness_timeout_
                    ):
                        time.sleep(_lepton_readiness_wait_time_)
                    if not self.ready():
                        raise RuntimeError(
                            f"KV {name} is not ready after"
                            f" {time.time() - start} seconds."
                        )
            else:
                raise ValueError(
                    f"KV {name} does not exist, and you have specified"
                    " create_if_not_exists=False."
                )

    def ready(self) -> bool:
        """
        Returns if the KV is ready to use.
        """
        # delete the key if it exists. We'll ignore any error as the delete call does not have side effects.
        try:
            self.delete(_lepton_readiness_test_key_)
        except Exception:
            pass
        ret = kv_api.put_key(
            self._conn,
            self._kv,
            _lepton_readiness_test_key_,
            _lepton_readiness_test_value_,
        )
        logger.trace(f"Readiness probe: {ret.status_code} {ret.content}")
        if ret.ok:
            return True
        elif ret.status_code == 500 and "no such host" in ret.json()["message"]:
            return False
        else:
            raise RuntimeError(
                "Failed to test the readiness of the KV. Error:"
                " {ret.status_code} {ret.content}."
            )

    async def async_wait(self):
        """
        Returns if the KV is ready to use, but wait for the KV to be ready asynchronously.
        """
        logger.trace("Waiting for KV to be ready.")
        start = time.time()
        while not self.ready() and time.time() - start < _lepton_readiness_timeout_:
            await asyncio.sleep(_lepton_readiness_wait_time_)
        if not self.ready():
            raise RuntimeError(
                f"KV {self._kv} is not ready after {time.time() - start} seconds."
            )

    def get(self, key: str) -> bytes:
        """
        Get the value of a key in the KV.
        """
        res = kv_api.get_key(self._conn, self._kv, key)
        if (
            res.status_code == 404
            or res.status_code == 500
            and "failed to get key" in res.json()["message"]
        ):
            raise KeyError(key)
        elif not res.ok:
            raise RuntimeError(
                f"Failed to get key {key} in KV {self._kv}. Error:"
                f" {res.status_code} {res.content}."
            )
        else:
            return res.content

    def put(self, key: str, value: Union[str, bytes]):
        """
        Put a key-value pair in the KV.
        """
        if len(key) > _lepton_max_key_length_:
            raise ValueError(
                f"Key length {len(key)} exceeds the maximum allowed length"
                f" {_lepton_max_key_length_}."
            )
        if len(value) > _lepton_max_value_length_:
            raise ValueError(
                f"Value length {len(value)} exceeds the maximum allowed length"
                f" {_lepton_max_value_length_}."
            )
        res = kv_api.put_key(self._conn, self._kv, key, value)
        if not res.ok:
            raise RuntimeError(
                f"Failed to put key {key} in KV {self._kv}. Error:"
                f" {res.status_code} {res.content}."
            )

    def delete(self, key: str):
        """
        Delete a key-value pair in the KV.
        """
        res = kv_api.delete_key(self._conn, self._kv, key)
        if res.status_code == 404:
            raise KeyError(key)
        elif not res.ok:
            raise RuntimeError(
                f"Failed to delete key {key} in KV {self._kv}. Error:"
                f" {res.status_code} {res.content}."
            )
