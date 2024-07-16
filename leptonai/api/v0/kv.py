import warnings

warnings.warn(
    "This module is deprecated and will be removed in the future. Please use"
    " leptonai.api.v1 instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Because most of the apis in kv do not return json, we will not use json_or_error here.
from typing import Union, Optional

from .connection import Connection


def list_kv(conn: Connection):
    """
    List KVs in the current workspace.
    """
    response = conn.get("/kv/namespaces")
    return response


def create_kv(conn: Connection, name: str):
    """
    Create a KV in the current workspace.
    """
    response = conn.post(f"/kv/namespaces/{name}")
    return response


def delete_kv(conn: Connection, name: str):
    """
    Delete a KV from the current workspace.
    """
    response = conn.delete(f"/kv/namespaces/{name}")
    return response


def get_key(conn: Connection, name: str, key: str):
    """
    Get the value of a key in the KV.
    """
    response = conn.get(f"/kv/namespaces/{name}/values/{key}")
    return response


def list_key(
    conn: Connection,
    name: str,
    cursor: Optional[int] = 0,
    limit: Optional[int] = 0,
    prefix: Optional[str] = None,
):
    """
    List keys in the KV.
    """
    response = conn.get(
        f"/kv/namespaces/{name}/keys",
        params={"cursor": cursor, "limit": limit, "prefix": prefix},
    )
    return response


def put_key(conn: Connection, name: str, key: str, value: Union[str, bytes]):
    """
    Put a key-value pair in the KV.
    """
    response = conn.post(f"/kv/namespaces/{name}/values/{key}", files={"value": value})
    return response


def delete_key(conn: Connection, name: str, key: str):
    """
    Delete a key-value pair from the KV.
    """
    response = conn.delete(f"/kv/namespaces/{name}/values/{key}")
    return response
