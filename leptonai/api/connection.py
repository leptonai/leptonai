"""
A utility package to abstract away the connection to the Lepton server.
"""
from typing import Dict, Optional
import requests
import warnings

from .util import create_header


class Connection:
    def __init__(self, url: str, token: Optional[str] = None):
        self._url = url
        self._token = token
        self._header = create_header(token)
        # In default, timeout for the API calls is set to 120 seconds.
        self._timeout = 120
        self._session = requests.Session()

    def _safe_add(self, kwargs: Dict) -> Dict:
        if "timeout" not in kwargs:
            kwargs["timeout"] = self._timeout
        if "headers" not in kwargs:
            kwargs["headers"] = self._header
        else:
            if "Authorization" in kwargs["headers"]:
                warnings.warn("Overriding Authorization header.")
            kwargs["headers"].update(self._header)
        return kwargs

    def get(self, path: str, *args, **kwargs):
        return self._session.get(self._url + path, *args, **self._safe_add(kwargs))

    def post(self, path: str, *args, **kwargs):
        return self._session.post(self._url + path, *args, **self._safe_add(kwargs))

    def patch(self, path: str, *args, **kwargs):
        return self._session.patch(self._url + path, *args, **self._safe_add(kwargs))

    def put(self, path: str, *args, **kwargs):
        return self._session.put(self._url + path, *args, **self._safe_add(kwargs))

    def delete(self, path: str, *args, **kwargs):
        return self._session.delete(self._url + path, *args, **self._safe_add(kwargs))

    def head(self, path: str, *args, **kwargs):
        return self._session.head(self._url + path, *args, **self._safe_add(kwargs))
