from typing import Optional, Union, List

from .api_resource import APIResourse
from .types.kv import ListKeysResponse, KV


class KVAPI(APIResourse):
    def _to_name(self, name_or_kv: Union[str, KV]) -> str:
        # Note: we do not use metadata.id_ or metadata.name here because these are not
        # the one used on the client side.
        return name_or_kv if isinstance(name_or_kv, str) else name_or_kv.name  # type: ignore

    def list_namespaces(self) -> List[KV]:
        """
        List KVs in the current workspace.
        """
        response = self._get("/kv/namespaces")
        return self.ensure_list(response, KV)

    def get_namespace(self, name_or_ns: Union[str, KV]) -> KV:
        """
        Get a KV in the current workspace.
        """
        response = self._get(f"/kv/namespaces/{self._to_name(name_or_ns)}")
        return self.ensure_type(response, KV)

    def create_namespace(self, name_or_ns: Union[str, KV]) -> bool:
        """
        Create a KV in the current workspace.
        """
        response = self._post(f"/kv/namespaces/{self._to_name(name_or_ns)}")
        return self.ensure_ok(response)

    def delete_namespace(self, name_or_ns: Union[str, KV]) -> bool:
        """
        Delete a KV from the current workspace.
        """
        response = self._delete(f"/kv/namespaces/{self._to_name(name_or_ns)}")
        return self.ensure_ok(response)

    def get(self, name_or_ns: Union[str, KV], key: str) -> bytes:
        """
        Get the value of a key in the KV.
        """
        response = self._get(f"/kv/namespaces/{self._to_name(name_or_ns)}/values/{key}")
        if response.status_code == 404:
            raise KeyError(f"Key {key} not found in KV {self._to_name(name_or_ns)}")
        # catch other errors
        self.ensure_ok(response)
        return response.content

    def put(self, name_or_ns: Union[str, KV], key: str, value: Union[str, bytes]):
        """
        Put a key-value pair in the KV.
        """
        response = self._post(
            f"/kv/namespaces/{self._to_name(name_or_ns)}/values/{key}",
            files={"value": value},
        )
        return self.ensure_ok(response)

    def delete(self, name_or_ns: Union[str, KV], key: str):
        """
        Delete a key-value pair from the KV.
        """
        response = self._delete(
            f"/kv/namespaces/{self._to_name(name_or_ns)}/values/{key}"
        )
        return self.ensure_ok(response)

    def list_keys(
        self,
        name_or_ns: Union[str, KV],
        cursor: Optional[int] = None,
        limit: Optional[int] = None,
        prefix: Optional[str] = None,
    ):
        """
        List keys in the KV.
        """
        response = self._get(
            f"/kv/namespaces/{self._to_name(name_or_ns)}/keys",
            params={"cursor": cursor, "limit": limit, "prefix": prefix},
        )
        return self.ensure_type(response, ListKeysResponse)
