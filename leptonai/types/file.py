"""
Utility class `File` for file handing, also using Lepton's object store for
large files.

On the client side, one can use `File` to wrap a file-like object, or a python byte,
or a string representing a URL, and pass it to the server:

    ```python
    # wrap a file-like object
    with open("path/to/file", "rb") as f:
        # pass file to the server
        file = File(f)  # base64 encoded string
    # wrap bytes
    content = b"....."
    file = File(content)  # base64 encoded string
    # wrap a URL
    content = "http://example.com"
    file = File(content)  # url
    ```

On the server side, one can then recover the file-like object from the
`File` object via:

    ```python
    # Assume that we have a variable "file" of type File.
    # get the content as a byte string
    content = file.get_content()
    # get a BytesIO object
    file_io = file.get_bytesio()
    # get a temporary file
    content = file.get_temp_file()
    ```
"""

import base64
from io import BytesIO
import requests
from typing import IO, Union
import re
import tempfile

from pydantic import BaseModel, validator

from leptonai.config import PYDANTIC_MAJOR_VERSION
from leptonai.util import _is_valid_url

_BASE64FILE_ENCODED_PREFIX = "data:application/octet-stream;base64,"


class File(BaseModel):
    content: Union[bytes, str]

    def __init__(self, content: Union[IO, bytes, str, "File"]):
        if isinstance(content, File):
            content = content.content
        if hasattr(content, "read"):
            content = content.read()  # type: ignore
        super().__init__(content=content)

    def __str__(self):
        return f"File(id={id(self)}) object"

    def __repr__(self):
        return str(self)

    def get_content(self) -> bytes:
        """
        Materialize the content into bytes, and return it.
        """
        if isinstance(self.content, bytes):
            pass
        elif isinstance(self.content, str):
            if _is_valid_url(self.content):
                # First, load from the URL, and then convert to BytesIO.
                try:
                    res = requests.get(self.content)
                    res.raise_for_status()
                except Exception:
                    raise ValueError(
                        f"Failed to download content from url: {self.content}"
                    )
                self.content = res.content
            elif re.match(r"^data:.*;base64,", self.content):
                self.content = base64.b64decode(self.content.split(",")[1])
            else:
                raise RuntimeError(
                    "You encountered a programming error. The File object passed"
                    " validation, but it seems that the content is neither a valid URL"
                    " nor a base64 encoded string. Please report this to Lepton. Got:"
                    f" {self.content}"
                )
        else:
            raise RuntimeError(
                "You encountered a programming error. The File object passed"
                " validation, but it seems that the content is illegal. Please report"
                f" this to Lepton. Got: {self.content}"
            )
        return self.content

    def get_bytesio(self) -> IO:
        """
        Returns a file-like object supporting read(), seek(), etc. Note that if
        the underlying content is a string of base64 encoded string, it will
        be downloaded/decoded to bytes first. If the content is a file-like object
        already, it will be seeked to the beginning.
        """
        return BytesIO(self.get_content())

    def get_temp_file(self, delete: bool = True):
        """
        Writes the content to a temporary file and returns the file. Note that the caller
        is responsible for the lifetime of the temporary file.
        """
        f = tempfile.NamedTemporaryFile(mode="w+b", delete=delete)
        f.write(self.get_content())
        f.flush()
        f.seek(0)
        return f

    @validator("content", pre=True)
    def validate_content(cls, content):
        if isinstance(content, bytes):
            return content
        elif isinstance(content, str):
            if _is_valid_url(content):
                return content
            elif re.match(r"^data:.*;base64,", content):
                return content
            elif re.match(r"^encoded:", content):
                # old FileParam input format. Convert to new format.
                return (
                    _BASE64FILE_ENCODED_PREFIX
                    + content[len("encoded:") :]  # noqa: E203
                )
            else:
                raise ValueError(
                    "When the content is a string, it must be a URL or a base64 encoded"
                    f" string. Got: {content}"
                )
        else:
            raise ValueError(
                "content must be a file-like object or bytes or a base64 encoded"
                f" string or a URL string. Got: {content}"
            )

    @staticmethod
    def encode(content: Union[bytes, str]) -> str:
        if isinstance(content, bytes):
            return _BASE64FILE_ENCODED_PREFIX + base64.b64encode(content).decode(
                "utf-8"
            )
        elif isinstance(content, str):
            return content
        else:
            raise ValueError(
                "content must be a file-like object or bytes or a base64 encoded"
                f" string. Got: {content}"
            )

    if PYDANTIC_MAJOR_VERSION <= 1:

        class Config:
            json_encoders = {Union[bytes, str, IO]: lambda v: File.encode(v)}
            # Backward compatibility to run smart_union if pydantic version is old.
            # See https://docs.pydantic.dev/1.10/usage/model_config/#smart-union for more details.
            smart_union = True

    else:
        from pydantic import field_serializer  # type: ignore

        @field_serializer("content")
        def _encode_content(self, content: Union[bytes, str], _) -> str:
            return self.encode(content)
