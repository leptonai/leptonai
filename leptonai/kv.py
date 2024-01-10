"""
Lepton's KV API is a simple key-value store. It is useful for storing small pieces of data
that are not directly related to a deployment, and can be accessed by multiple deployments.
For example, you can use the KV API and the Queue API to build a distributed task manager.
"""

import asyncio
from pydantic import BaseModel
from requests import Response
import time
from typing import List, Optional, Union

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

_kv_name_resolution_message = """
You have encountered a name resolution error when accessing the KV. This is likely
because you are using a relatively new KV, and as our KV backend uses DNS to resolve
the KV service address, it may take some time for the DNS to be updated and propagated
to the DNS server you are using. Please try again in a few minutes. This is not
a bug of our system, but due to the nature of the distributed DNS resolution system.
"""


def _maybe_dns_message(res: Response) -> str:
    if res.status_code == 500 and "no such host" in res.json()["message"]:
        return _kv_name_resolution_message
    else:
        return ""


class PartialKeyList(BaseModel):
    """
    A partial list of keys in a KV, also including the cursor for the next page.
    """

    keys: List[str]
    cursor: Optional[int] = None


def _is_a_kv_not_ready_response(response: Response) -> bool:
    """
    Returns if the response is equivalent to a KV not ready response.
    """
    return response.status_code == 500 and "no such host" in response.json()["message"]


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

    When the KV is ready, you can use `my_kv.put(key, value)` to put a key-value pair, `my_kv.get(key)`
    to get the value of a key, and `my_kv.delete(key)` to delete a key-value pair. The key should be
    a valid python string and the value should be either a valid python string or bytes.

    Alternatively, use `my_kv[key] = value` to put a key-value pair, `my_kv[key]` to get the value of a key,
    and `del my_kv[key]` to delete a key-value pair.
    """

    @staticmethod
    def list_kv(conn: Optional[Connection] = None) -> List[str]:
        """
        List KVs in the current workspace.
        """
        conn = conn if conn else workspace_api.current_connection()
        res = kv_api.list_kv(conn)
        if not res.ok:
            raise RuntimeError(
                "Failed to list KVs in the current workspace. Error:"
                f" {res.status_code} {res.content}."
            )
        return [s["name"] for s in res.json()]

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
                    # It seems to be always good to first sleep for a while for the
                    # remote KV to have the chance to finish creation.
                    time.sleep(_lepton_readiness_wait_time_)
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
            try:
                self.delete(_lepton_readiness_test_key_)
            except Exception:
                pass
            return True
        elif ret.status_code == 500 and "no such host" in ret.json()["message"]:
            logger.trace(f"KV not ready: {ret.status_code} {ret.content}")
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

    def keys(
        self,
        cursor: Optional[int] = 0,
        limit: Optional[int] = 0,
        prefix: Optional[str] = None,
    ) -> PartialKeyList:
        """
        List keys in the KV.
        """
        res = kv_api.list_key(self._conn, self._kv, cursor, limit, prefix)
        if not res.ok:
            raise RuntimeError(
                f"Failed to list keys in KV {self._kv}. Error:"
                f" {res.status_code} {res.content}.{_maybe_dns_message(res)}"
            )
        return PartialKeyList.parse_raw(res.content)

    def get(self, key: str) -> bytes:
        """
        Get the value of a key in the KV.
        """
        res = kv_api.get_key(self._conn, self._kv, key)
        if res.status_code == 404:
            logger.trace(f"key error: {res.status_code} {res.content}")
            raise KeyError(key)
        elif not res.ok:
            logger.trace(f"key error other than 404: {res.status_code} {res.content}")
            raise RuntimeError(
                f"Failed to get key {key} in KV {self._kv}. Error:"
                f" {res.status_code} {res.content}.{_maybe_dns_message(res)}"
            )
        else:
            return res.content

    def put(self, key: str, value: Union[str, bytes]) -> None:
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
            logger.trace(f"key put error: {res.status_code} {res.content}")
            raise RuntimeError(
                f"Failed to put key {key} in KV {self._kv}. Error:"
                f" {res.status_code} {res.content}.{_maybe_dns_message(res)}"
            )

    def delete(self, key: str) -> None:
        """
        Delete a key-value pair in the KV.

        Note that if a key does not exist in the KV, this function will not raise an error.
        """
        res = kv_api.delete_key(self._conn, self._kv, key)
        if not res.ok:
            logger.trace(f"key delete error: {res.status_code} {res.content}")
            raise RuntimeError(
                f"Failed to delete key {key} in KV {self._kv}. Error:"
                f" {res.status_code} {res.content}.{_maybe_dns_message(res)}"
            )

    def __getitem__(self, key: str) -> bytes:
        return self.get(key)

    def __setitem__(self, key: str, value: Union[str, bytes]):
        self.put(key, value)

    def __delitem__(self, key: str):
        self.delete(key)
