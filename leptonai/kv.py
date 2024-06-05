"""
Lepton's KV API is a simple key-value store. It is useful for storing small pieces of data
that are not directly related to a deployment, and can be accessed by multiple deployments.
For example, you can use the KV API and the Queue API to build a distributed task manager.
"""

import asyncio
import time
from typing import List, Optional, Union

from loguru import logger

from leptonai.api.v1.client import APIClient
from leptonai.api.v1.kv import ListKeysResponse


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

    When the KV is ready, you can use `my_kv.put(key, value)` to put a key-value pair, `my_kv.get(key)`
    to get the value of a key, and `my_kv.delete(key)` to delete a key-value pair. The key should be
    a valid python string and the value should be either a valid python string or bytes.

    Alternatively, use `my_kv[key] = value` to put a key-value pair, `my_kv[key]` to get the value of a key,
    and `del my_kv[key]` to delete a key-value pair.
    """

    @staticmethod
    def list_kv() -> List[str]:
        """
        List KVs in the current workspace.
        """
        client = APIClient()
        kvs = client.kv.list_namespaces()
        logger.info(f"List of KVs: {kvs}")
        return [kv.metadata.name for kv in kvs]  # type: ignore

    @staticmethod
    def create_kv(
        name: str,
        wait_for_creation: bool = True,
    ) -> "KV":
        """
        Create a KV.
        """
        kv_instance = KV(
            name,
            create_if_not_exists=True,
            error_if_exists=True,
            wait_for_creation=wait_for_creation,
        )
        return kv_instance

    @staticmethod
    def get_kv(name: str) -> "KV":
        """
        Get an existing KV.
        """
        kv_instance = KV(name, create_if_not_exists=False)
        return kv_instance

    @staticmethod
    def delete_kv(name: Union["KV", str]):
        """
        Delete a KV.
        """
        if isinstance(name, KV):
            name = name._kv
        client = APIClient()
        client.kv.delete_namespace(name)

    def __init__(
        self,
        name: str,
        create_if_not_exists: bool = False,
        error_if_exists: bool = False,
        wait_for_creation: bool = True,
        api_client: Optional[APIClient] = None,
    ):
        """
        Initializes a KV.

        :param str name: the name of the KV
        :param bool create_if_not_exists: if True, create the KV if it does not exist
        :param bool error_if_exists: if True, raise an error if the KV already exists
        :param bool wait_for_creation: if True, wait for the KV to be ready
        :param Connection conn: the connection to use. If None, use the default workspace connection.
        """
        self._api_client = api_client or APIClient()
        kvs = self._api_client.kv.list_namespaces()
        if any(kv.metadata.name == name for kv in kvs):
            if error_if_exists:
                raise ValueError(
                    f"KV {name} already exists, and you have specified"
                    " error_if_exists=True."
                )
            else:
                self._kv = name
        else:
            if create_if_not_exists:
                self._api_client.kv.create_namespace(name)
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
        try:
            _ = self._api_client.kv.get_namespace(self._kv)
            return True
        except Exception:
            return False

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
    ) -> ListKeysResponse:
        """
        List keys in the KV.
        """
        return self._api_client.kv.list_keys(self._kv, cursor, limit, prefix)

    def get(self, key: str) -> bytes:
        """
        Get the value of a key in the KV.
        """
        return self._api_client.kv.get(self._kv, key)

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
        self._api_client.kv.put(self._kv, key, value)

    def delete(self, key: str) -> None:
        """
        Delete a key-value pair in the KV.

        Note that if a key does not exist in the KV, this function will not raise an error.
        """
        self._api_client.kv.delete(self._kv, key)

    def __getitem__(self, key: str) -> bytes:
        return self.get(key)

    def __setitem__(self, key: str, value: Union[str, bytes]):
        self.put(key, value)

    def __delitem__(self, key: str):
        self.delete(key)
