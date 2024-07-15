from typing import Optional, IO

from leptonai.api.v1.api_resource import APIResourse
from leptonai.api.v1.types.object_storage import ListObjectsResponse


class ObjectStorageAPI(APIResourse):
    def list(
        self, prefix: Optional[str] = None, is_public=False
    ) -> ListObjectsResponse:
        bucket_param = "public" if is_public else "private"
        maybe_prefix = {"prefix": prefix} if prefix else {}
        response = self._get(f"/object_storage/{bucket_param}", params=maybe_prefix)
        return self.ensure_type(response, ListObjectsResponse)

    def delete(self, key, is_public=False) -> bool:
        bucket_param = "public" if is_public else "private"
        response = self._delete(f"/object_storage/{bucket_param}/{key}")
        return self.ensure_ok(response)

    def put(self, key: str, file_like: IO, public):
        bucket_param = "public" if public else "private"
        response = self._put(
            f"/object_storage/{bucket_param}_presigned/{key}", file_like
        )
        self.ensure_ok(response)

    def get(
        self, key: str, is_public=False, return_url: bool = False, stream: bool = False
    ):
        bucket_param = "public" if is_public else "private_presigned"
        response = self._get(
            f"/object_storage/{bucket_param}/{key}",
            allow_redirects=not return_url,
            stream=stream,
        )
        self.ensure_ok(response)
        return response
