"""
Lepton's Object store provides a simple way to transmit small files between deployments,
and between the deployment and the client.
"""

from abc import ABC
from contextlib import nullcontext
import os
import tempfile
from typing import Optional, Union, IO

from leptonai.api.v0 import objectstore as oss_api
from leptonai.api.v0.connection import Connection
from leptonai.api.v0 import workspace as workspace_api

from leptonai.photon.types.file import File


class ObjectStoreClientBase(ABC):
    """
    The base abstract class for all object store clients. This class should not be
    instantiated directly. Instead, use the Public or Private class to access the
    public or private object store.
    """

    bucket_name = "this_needs_to_be_overridden_by_derived_classes"
    is_public = None

    def __init__(self, conn: Optional[Connection] = None):
        self._conn = conn if conn else workspace_api.current_connection()

    def get(self, key: str, return_url: bool = False):
        """
        Gets the object with the given key.

        If return_url is True, the function will return the url of the object. Note
        that if the object is private, the url will be a presigned url that can be
        used to access the object, and the url will expire after 900 seconds (15
        minutes). If return_url is False, a temporary file will be created to store
        the content of the object, and the temporary file object will be returned.

        It is recommended that you use a with statement to manage the lifetime of
        the returned file object. For example:
            ```
            with my_object_store_client.get(key) as f:
                # do something with f.
            ```
        Alternatively, you can also manually close the file object after you are
        done with it.
        """
        res = oss_api.get(
            self._conn, key, self.bucket_name, return_url=return_url, stream=return_url
        )
        if not res.ok:
            raise RuntimeError(f"Failed to get object {key}. Error: {res.status_code}.")
        if return_url:
            return res.headers["location"]
        else:
            # We need to read the content and then return the temporary file.
            f = tempfile.NamedTemporaryFile()
            for chunk in res.iter_content(chunk_size=1024):
                f.write(chunk)
            f.flush()
            f.seek(0)
            return f

    def put(self, key: str, file_like: Union[IO, str, File]):
        """
        Upload a file to the current workspace with the given key. After the file is uploaded,
        returns the url of the object that can be used to access the object.

        Note that if an object with the same key already exists, it will be overwritten.
        """
        if isinstance(file_like, File):
            context = nullcontext(file_like.get_bytesio())
        elif hasattr(file_like, "read"):
            context = nullcontext(file_like)
        elif isinstance(file_like, str) and os.path.isfile(file_like):
            context = open(file_like, "rb")
        else:
            raise TypeError(
                "file_like must be either a string, a lepton File class object, or "
                f"a file-like object, but got {type(file_like)}."
            )
        with context as opened_file:
            res = oss_api.put(self._conn, key, opened_file, self.bucket_name)
            if not res.ok:
                raise RuntimeError(
                    f"Failed to put object {key}. Error:"
                    f" {res.status_code} {res.content}."
                )
            # After upload, we return the url of the object.
            res = oss_api.get(self._conn, key, self.bucket_name, return_url=True)
            if not res.ok:
                raise RuntimeError(
                    f"Failed to get object {key}. Error:"
                    f" {res.status_code} {res.content}."
                )
            return res.headers["location"]

    def delete(self, key: str):
        """
        Deletes the object with the given key. Note that if the object does not exist,
        this function will not raise an error.
        """
        res = oss_api.delete(self._conn, key, self.bucket_name)
        if not res.ok:
            raise RuntimeError(
                f"Failed to delete object {key}. Error:"
                f" {res.status_code} {res.content}."
            )

    # implementation note: we use "list_object" instead of "list" to avoid polluting
    # the python reserved keyword "list".
    def list_objects(self, prefix: Optional[str] = None):
        """
        Lists all objects in the current workspace with the given prefix. The returned
        object is a list of dictionaries, each of which contains the following keys: "key"
        (the key of the object), "size" (the size of the object in bytes).
        """
        res = oss_api.list_objects(self._conn, self.bucket_name, prefix=prefix)
        if not res.ok:
            raise RuntimeError(
                f"Failed to list objects. Error: {res.status_code} {res.content}."
            )
        return res.json()["items"]


class PublicObjectStore(ObjectStoreClientBase):
    bucket_name = "public"
    is_public = True


class PrivateObjectStore(ObjectStoreClientBase):
    bucket_name = "private"
    is_public = False


def ObjectStore(bucket: str) -> ObjectStoreClientBase:
    """
    Returns an object store client for the given bucket. The bucket can be either
    "public" or "private".
    """
    if bucket == "public":
        return PublicObjectStore()
    elif bucket == "private":
        return PrivateObjectStore()
    else:
        raise ValueError(
            f"Invalid bucket name {bucket}: must be either public or private."
        )
