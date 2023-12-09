import base64
from io import BytesIO
import warnings

from pydantic import BaseModel, validator

from leptonai.config import PYDANTIC_MAJOR_VERSION


_BASE64FILE_ENCODED_PREFIX = "encoded:"


class FileParam(BaseModel):
    content: bytes

    # allow creating FileParam with position args
    def __init__(self, content: bytes):
        warnings.warn(
            "FileParam is deprecated and may be removed in a future version. Instead,"
            " use lepton.photon.types.File, by passing it a bytes, a file-like object,"
            " a string representing a URL. File can be a drop-in replacement for"
            " FileParam.",
            DeprecationWarning,
        )
        super().__init__(content=content)

    def __str__(self):
        return f"FileParam(id={id(self)}) {len(self.content)} Bytes"

    def __repr__(self):
        return str(self)

    # TODO: cached property?
    @property
    def file(self):
        return BytesIO(self.content)

    @validator("content", pre=True)
    def validate_content(cls, content):
        # when users create a FileParam, content is a file-like object
        if hasattr(content, "read"):
            return content.read()
        elif isinstance(content, bytes):
            return content
        elif isinstance(content, str):
            # when the FileParam is created from a request, content is a base64 encoded string
            if content.startswith(_BASE64FILE_ENCODED_PREFIX):
                return base64.b64decode(
                    content[len(_BASE64FILE_ENCODED_PREFIX) :].encode(  # noqa: E203
                        "utf-8"
                    )
                )
            else:
                return content.encode("utf-8")
        else:
            raise ValueError(
                "content must be a file-like object or bytes or a base64 encoded"
                f" string: {content}"
            )

    @staticmethod
    def encode(content: bytes) -> str:
        return _BASE64FILE_ENCODED_PREFIX + base64.b64encode(content).decode("utf-8")

    if PYDANTIC_MAJOR_VERSION <= 1:

        class Config:
            json_encoders = {bytes: lambda v: FileParam.encode(v)}

    else:
        from pydantic import field_serializer  # type: ignore

        @field_serializer("content")
        def _encode_content(self, content: bytes, _) -> str:
            return self.encode(content)
