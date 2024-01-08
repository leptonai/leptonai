import requests
from typing import IO, Optional

from .connection import Connection


def get(
    conn: Connection,
    key: str,
    bucket_name: str,
    return_url: bool = False,
    stream: bool = False,
):
    """
    Obtains an object url that belongs to the current workspace.

    If return_url is True, the function will return the url of the object instead
    of the content of the object. Otherwise, the function will return the content
    of the object.
    """
    presigned_bucket_name = (
        bucket_name if bucket_name == "public" else f"{bucket_name}_presigned"
    )
    response = conn.get(
        f"/object_storage/{presigned_bucket_name}/{key}",
        stream=stream,
        allow_redirects=not return_url,
    )
    return response


def put(conn: Connection, key: str, file_like: IO, bucket_name: str):
    """
    Upload a file to the current workspace.
    """
    response = conn.put(
        f"/object_storage/{bucket_name}_presigned/{key}", allow_redirects=False
    )
    if response.is_redirect:
        url = response.json()["url"]
        response = requests.put(url, data=file_like, stream=True)
        return response
    else:
        # For all other cases, we directly return the response to the caller.
        # Note that this most likely means that the response is an error, unless
        # we found a bug in the server.
        return response


def list_objects(conn: Connection, bucket_name: str, prefix: Optional[str] = None):
    """
    List all objects in the current workspace.
    """
    maybe_prefix = {"prefix": prefix} if prefix else {}
    response = conn.get(f"/object_storage/{bucket_name}/", params=maybe_prefix)
    return response


def delete(conn: Connection, key: str, bucket_name: str):
    """
    Delete an object from the current workspace.
    """
    response = conn.delete(f"/object_storage/{bucket_name}/{key}")
    return response
