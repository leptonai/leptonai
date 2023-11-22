import base64
from io import BytesIO
import os
import re
import tempfile
from typing import Union, IO, Type

from PIL.Image import Image
import requests

from . import FileParam
from leptonai.util import _is_valid_url
from .responses import StreamingResponse, JPEGResponse, PNGResponse


def to_bool(s: str) -> bool:
    """
    Convert a string to a boolean value.
    """
    if not isinstance(s, str):
        raise TypeError(f"Expected a string, got {type(s)}")
    true_values = ("yes", "true", "t", "1", "y", "on", "aye", "yea")
    false_values = ("no", "false", "f", "0", "n", "off", "nay", "")
    s = s.lower()
    if s in true_values:
        return True
    elif s in false_values:
        return False
    else:
        raise ValueError(
            f"Invalid boolean value: {s}. Valid true values: {true_values}. Valid false"
            f" values: {false_values}."
        )


def _make_temp_file(content: bytes) -> IO:
    """
    A utility function to write bytes to a temporary file. This is useful
    if one needs to pass a file object to a function, but only has bytes.
    """
    f = tempfile.NamedTemporaryFile()
    f.write(content)
    return f


def get_file_content(
    src: Union[FileParam, str, bytes],
    allow_local_file: bool = False,
    return_file: bool = False,
) -> Union[bytes, IO]:
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
        allow_local_file: if True, we will allow reading from local file system.
        return_file: if True, we will return a file object instead of bytes. If False (default),
            we will return bytes.
    Returns:
        content: the file content in bytes, or a file object if return_file is True.
    """
    if isinstance(src, FileParam):
        return _make_temp_file(src.content) if return_file else src.content
    elif isinstance(src, str):
        if _is_valid_url(src):
            # If the source is a valid url, we will download the content and return it.
            try:
                content = requests.get(src).content
            except Exception:
                raise ValueError(f"Failed to download content from url: {src}")
            return _make_temp_file(content) if return_file else content
        elif os.path.exists(src) and allow_local_file:
            if return_file:
                return open(src, "rb")
            else:
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
                content = base64.b64decode(src)
            except Exception:
                raise ValueError(
                    "Failed to decode base64 string:"
                    f" {src if len(src) < 100 else src[:100] + '...'}"
                )
            return _make_temp_file(content) if return_file else content
        # If any of the above fails, we will raise an error.
        raise ValueError(
            "Failed to get file content from source:"
            f" {src if len(src) < 100 else src[:100] + '...'}"
        )
    elif isinstance(src, bytes):
        # Fallback: if the content is already bytes, do nothing.
        return _make_temp_file(src) if return_file else src
    # Anything not covered above is not supported.
    raise TypeError(
        "src must be a FileParam, a url, a local file path, a base64-encoded string,"
        f" or raw bytes. Got {type(src)}"
    )


def make_img_response(
    img: Image, format: str, ResponseType: Type[StreamingResponse]
) -> StreamingResponse:
    """
    Convert an image to a response.
    """
    img_byte_array = BytesIO()
    img.save(img_byte_array, format=format)
    img_byte_array.seek(0)
    return ResponseType(img_byte_array)


def make_jpeg_response(img: Image) -> JPEGResponse:
    """
    Convert an image to a JPEG response.
    """
    return make_img_response(img, "JPEG", JPEGResponse)


def make_png_response(img: Image) -> PNGResponse:
    """
    Convert an image to a PNG response.
    """
    return make_img_response(img, "PNG", PNGResponse)
