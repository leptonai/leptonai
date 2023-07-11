from urllib.parse import urljoin, urlparse
import warnings

from backports.cached_property import cached_property
from fastapi.encoders import jsonable_encoder
import requests

from leptonai.util import (
    get_full_workspace_url,
    get_full_workspace_api_url,
)
from .api.deployment import list_deployment


def _is_valid_url(candidate_str):
    parsed = urlparse(candidate_str)
    return parsed.scheme != "" and parsed.netloc != ""


def _is_local_url(candidate_str):
    parsed = urlparse(candidate_str)
    local_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
    return parsed.netloc.lower() in local_hosts


class Workspace:
    """
    The lepton python class that holds necessary info to access a workspace.

    A workspace allows one to access a set of deployments under this workspace.
    Currently, we do not support local workspaces - all workspaces are remote.
    """

    def __init__(self, workspace_name, token=None):
        """
        Creates a Lepton workspace.

        Args:
            workspace_name (str): The workspace name.
            token (str, optional): The token to use for authentication. Defaults to None.
        """
        self.workspace_name = workspace_name
        self.token = token

    @cached_property
    def _workspace_deployments(self):
        return list_deployment(
            get_full_workspace_api_url(self.workspace_name), self.token
        )

    @cached_property
    def _workspace_deployments_names(self):
        return [deployment["name"] for deployment in self._workspace_deployments]

    def list_deployments(self):
        """
        List all deployments on this workspace.
        """
        return self._workspace_deployments_names

    def client(self, deployment_name, token=None):
        """
        Get the client to call a deployment in this workspace. Note that this
        does not actually start a deployment - it only creates a client that
        can call the currently active deployment.

        Args:
            deployment_name (str): The deployment name.
            token (str, optional): The token to use for authentication. If None,
                the default is to use the token passed in when the workspace was
                created. Defaults to None.
        """
        if deployment_name not in self._workspace_deployments_names:
            raise ValueError(
                f"Deployment {deployment_name} not found in workspace"
                f" {self.workspace_name}."
            )
        return Client(
            self.workspace_name, deployment_name, token if token else self.token
        )


class Client:
    """
    The lepton python client that calls a deployment in a workspace.

    A Client gives pythonic access to the functions defined in a deployment. For
    example, if a deployment defines two functions, `foo` and `bar`, they can
    usually be accessed via two openapi endpoint urls, `/foo` and `/bar`. The
    python equivalent will then be `client.foo` and `client.bar`, as one would
    expect a python class may have.

    The client can be initialized with a workspace name and the deployment name,
    or a full URL to the deployment's endpoint. For example, if the workspace is
    `my-workspace` and the deployment is `my-deployment`, the client can be created
    via
        client = Client("my-workspace", "my-deployment", token=MY_TOKEN)
    or via the full URL (given you are using the public cloud deployment):
        client = Client("https://my-workspace-my-deployment.cloud.lepton.ai", token=MY_TOKEN)
    """

    # TODO: add support for creating client with name/id
    def __init__(self, workspace_or_url, deployment=None, token=None):
        """
        Initializes a Lepton client that calls a deployment in a workspace.

        Args:
            workspace_or_url (str): The workspace name, or a full URL to the deployment's
                endpoint.
            deployment (str, optional): The deployment name. If a full URL is passed
                in, deployment can be None.
            token (str, optional): The token to use for authentication. Defaults to None.

        Implementation Note: when one uses a full URL, the client accesses the deployment
        specific endpoint directly. This endpoint may have a certain delay, and may not be
        immediately available after the deployment is created. when one uses a workspace
        name and the deployment name, the client accesses the workspace endpoint and uses
        the deployment name as a header. This is the recommended way to use the client.
        We may remove the ability to use a full URL in the future.
        """
        if _is_valid_url(workspace_or_url):
            if not _is_local_url(workspace_or_url):
                warnings.warn(
                    "Explicitly passing in a remote URL is deprecated, and may be"
                    " removed in the future.",
                    DeprecationWarning,
                )
            self.url = workspace_or_url
        else:
            # TODO: sanity check if the workspace name is legit.
            self.url = get_full_workspace_url(workspace_or_url)
        self._session = requests.Session()
        if deployment is None:
            if not _is_local_url(workspace_or_url):
                warnings.warn(
                    "Remote execution without an explicit deployment is deprecated,"
                    " and may be removed in the future.",
                    DeprecationWarning,
                )
        else:
            # TODO: at the right time, change it to X-Lepton-Deployment
            self._session.headers.update({"Deployment": deployment})
            # As a future-proof approach, we pass in both at the moment, so the backend
            # code can land asynchronously.
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
                res = self._post(
                    name,
                    json=jsonable_encoder(kwargs),
                )
                res.raise_for_status()
                return res.json()

            _method.__name__ = name
            self._path_cache[name] = _method
        return self._path_cache[name]

    @cached_property
    def openapi(self):
        """
        Returns the OpenAPI specification of the deployment, or None if the
        deployment does not have an openapi specified.
        """
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
