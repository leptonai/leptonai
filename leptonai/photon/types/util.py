import base64
import os
import re
from typing import Union

import requests

from . import FileParam
from leptonai.util import _is_valid_url


def get_file_content(
    src: Union[FileParam, str, bytes], allow_local_file: bool = False
) -> bytes:
    """
    Gets the file content from a source.

    The source can be one of the following: a FileParam object, a url, a local file path,
    a base64-encoded string, or raw bytes. For a base64-encoded string,
    we support two formats: (1) raw base64-encoded string, or (2) a string that starts with
    "data:" and contains a base64-encoded string, conforming to the RFC 2397 standard.

    Local file path is only supported if allow_local_file is True. This is for safety reasons,
    as we do not want to accidentally read files from the local file system when running a
    remote service.

    Inputs:
        src: the source of the file content.
    Returns:
        content: the file content in bytes.
    """
    if isinstance(src, FileParam):
        return src.content
    elif isinstance(src, str):
        if _is_valid_url(src):
            # If the source is a valid url, we will download the content and return it.
            try:
                content = requests.get(src).content
            except Exception:
                raise ValueError(f"Failed to download content from url: {src}")
            return content
        elif os.path.exists(src) and allow_local_file:
            with open(src, "rb") as f:
                return f.read()
        elif src.startswith("data:"):
            # Extract the leading base64 string, and decode it.
            # See https://tools.ietf.org/html/rfc2397 for the RFC 2397 standard.
            # Note: we will ignore the media type and encoding, as we only support
            # base64 encoding.
            pattern = re.compile(r"data:.*?;base64,(.*)")
            match = pattern.match(src)
            if match:
                try:
                    return base64.b64decode(match.group(1))
                except Exception:
                    raise ValueError(
                        "Invalid base64 string:"
                        f" {src if len(src) < 100 else src[:100] + '...'}"
                    )
        elif len(src) % 4 == 0 and re.match(r"^[A-Za-z0-9+/]*={0,2}$", src):
            # Last resort: we will try to decode the string as a base64 string.
            try:
                return base64.b64decode(src)
            except Exception:
                raise ValueError(
                    "Failed to decode base64 string:"
                    f" {src if len(src) < 100 else src[:100] + '...'}"
                )
        # If any of the above fails, we will raise an error.
        raise ValueError(
            "Failed to get file content from source:"
            f" {src if len(src) < 100 else src[:100] + '...'}"
        )
    elif isinstance(src, bytes):
        # Fallback: if the content is already bytes, do nothing.
        return src
    # Anything not covered above is not supported.
    raise TypeError(
        "src must be a FileParam, a url, a local file path, a base64-encoded string,"
        f" or raw bytes. Got {type(src)}"
    )
