from urllib.parse import urljoin

from backports.cached_property import cached_property
import requests


class Client:
    # TODO: add support for creating client with name/id
    def __init__(self, url):
        self.url = url
        self._session = requests.Session()
        self._path_cache = {}

    # Normal usages will go through then `__getattr__` path (which triggers
    # `_post_path` and `_post`). Directly using `_post` and `_get` is
    # discouraged, only when accessing endpoints that are not defined via
    # Photon.
    def _get(self, path, *args, **kwargs):
        return self._session.get(urljoin(self.url, path), *args, **kwargs)

    def _post(self, path, *args, **kwargs):
        return self._session.post(urljoin(self.url, path), *args, **kwargs)

    def _post_path(self, name):
        if name not in self._path_cache:

            def _method(**kwargs):
                return self._post(name, json=kwargs).json()

            _method.__name__ = name
            self._path_cache[name] = _method
        return self._path_cache[name]

    @cached_property
    def openapi(self):
        try:
            return self._get("/openapi.json").json()
        except requests.exceptions.ConnectionError:
            return None

    def paths(self):
        if self.openapi is not None:
            return self.openapi["paths"].keys()
        return []

    def __getattr__(self, name):
        if f"/{name}" in self.paths():
            return self._post_path(name)
        raise AttributeError(name)
