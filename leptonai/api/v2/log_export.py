from typing import Optional, Tuple
from urllib.parse import quote

from requests import Response

from .api_resource import APIResourse
from .log import _parse_retry_after
from .types.log_export import LogExport, LogExportCreateRequest


class LogExportAPIError(RuntimeError):
    """A non-2xx `/logs/exports` response, with the server's typed details.

    `reason` is `details.reason` from the service error body (for example
    `export_not_ready` or `unsupported_range`). Authentication middleware can
    answer with only code/message, so it may be `None`.
    """

    def __init__(self, response: Response, body: Optional[dict]):
        body = body if isinstance(body, dict) else {}
        details = body.get("details")
        details = details if isinstance(details, dict) else {}
        self.status_code: int = response.status_code
        self.code: Optional[str] = body.get("code")
        self.reason: Optional[str] = details.get("reason")
        self.export_id: Optional[str] = details.get("export_id")
        self.available_start: Optional[str] = details.get("available_start")
        self.available_end: Optional[str] = details.get("available_end")
        self.max_range_seconds: Optional[str] = details.get("max_range_seconds")
        self.retry_after: Optional[float] = _parse_retry_after(response)
        self.request_id: Optional[str] = response.headers.get("X-Request-ID")
        message = body.get("message") or response.reason or "request failed"
        super().__init__(
            f"{response.status_code} {self.reason or self.code or 'error'}: {message}"
        )


class LogExportAPI(APIResourse):
    """Bulk log exports (create, poll, download) under `/logs/exports`.

    The server returns absolute `status_url`/`download_url` values; this class
    deliberately builds paths from the export ID instead, so the bearer header
    is only ever sent to the configured workspace URL.
    """

    def _raise_for_status(self, response: Response) -> Response:
        if response.status_code < 400:
            return response
        try:
            body = response.json()
        except Exception:
            body = None
        raise LogExportAPIError(response, body)

    @staticmethod
    def _path(export_id: str) -> str:
        return f"/logs/exports/{quote(export_id, safe='')}"

    def create(
        self, request: LogExportCreateRequest, idempotency_key: str
    ) -> Tuple[LogExport, Optional[float]]:
        """Create (or replay) an export; returns it with any Retry-After hint.

        Reuse the same `idempotency_key` and request to retry an uncertain
        submission; a changed request under the same key is a 409 conflict.
        """
        response = self._raise_for_status(
            self._post(
                "/logs/exports",
                json=request.dict(by_alias=True),
                headers={"Idempotency-Key": idempotency_key},
            )
        )
        return LogExport(**response.json()), _parse_retry_after(response)

    def get(self, export_id: str) -> Tuple[LogExport, Optional[float]]:
        """Return the export's current status with any Retry-After hint."""
        response = self._raise_for_status(self._get(self._path(export_id)))
        return LogExport(**response.json()), _parse_retry_after(response)

    def download(self, export_id: str, timeout: Optional[float] = None) -> Response:
        """Open the NDJSON artifact as a streaming response.

        The caller must consume and close the response. The stream has no
        Content-Length or resume support; a transfer interrupted after the
        headers surfaces as a `requests` exception while iterating.
        """
        kwargs = {"stream": True}
        if timeout is not None:
            kwargs["timeout"] = timeout
        response = self._get(f"{self._path(export_id)}/download", **kwargs)
        try:
            return self._raise_for_status(response)
        except LogExportAPIError:
            response.close()
            raise
