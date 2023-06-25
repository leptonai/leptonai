from urllib.parse import urljoin, urlparse
import warnings

from backports.cached_property import cached_property
import requests


def _is_valid_url(candidate_str):
    parsed = urlparse(candidate_str)
    return parsed.scheme != "" and parsed.netloc != ""


def _is_local_url(candidate_str):
    parsed = urlparse(candidate_str)
    local_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
    return parsed.netloc.lower() in local_hosts


class Client:
    # TODO: add support for creating client with name/id
    def __init__(self, workspace, deployment=None, token=None):
        """
        Initializes a Lepton client that calls a deployment in a workspace.

        Args:
            workspace (str): The workspace name.
            deployment (str): The deployment name.
            token (str, optional): The token to use for authentication. Defaults to None.
        """
        if _is_valid_url(workspace):
            if not _is_local_url(workspace):
                warnings.warn(
                    (
                        "Explicitly passing in a remote URL is deprecated, and may be"
                        " removed in the future."
                    ),
                    DeprecationWarning,
                )
            self.url = workspace
        else:
            # TODO: sanity check if the workspace name is legit.
            self.url = f"https://{workspace}.cloud.lepton.ai"
        self._session = requests.Session()
        if deployment is None:
            if not _is_local_url(workspace):
                warnings.warn(
                    (
                        "Remote execution without an explicit deployment is deprecated,"
                        " and may be removed in the future."
                    ),
                    DeprecationWarning,
                )
        else:
            self._session.headers.update({"X-Lepton-Deployment": deployment})
        if token is not None:
            self._session.headers.update({"Authorization": f"Bearer {token}"})
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

    def __dir__(self):
        # Note: self.paths() returns the paths with the '/' prefix, so we will
        # remove that part.
        return super().__dir__() + list(p[1:] for p in self.paths())
