from typing import Optional, List
from urllib.parse import urljoin, urlparse
import warnings

from backports.cached_property import cached_property
from fastapi.encoders import jsonable_encoder
import requests

from leptonai.api.workspace import get_full_workspace_api_url
from .api import deployment, APIError


def _is_valid_url(candidate_str):
    parsed = urlparse(candidate_str)
    return parsed.scheme != "" and parsed.netloc != ""


def _is_local_url(candidate_str):
    parsed = urlparse(candidate_str)
    local_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
    return parsed.netloc.lower() in local_hosts


def local(port=8080):
    """
    Create a connection string for a local deployment. This is useful for testing
    purposes, and does not require you to type the local IP address repeatedly.

    Usage:
        client = Client(local())
        client.foo()

    Args:
        port (int, optional): The port number. Defaults to 8080.
    Returns:
        str: The connection string.
    """
    return f"http://localhost:{port}"


class Workspace:
    """
    The lepton python class that holds necessary info to access a workspace.

    A workspace allows one to access a set of deployments under this workspace.
    Currently, we do not support local workspaces - all workspaces are remote.
    """

    def __init__(self, workspace_id: str, token: Optional[str] = None):
        """
        Creates a Lepton workspace.

        Args:
            workspace_id (str): The workspace id.
            token (str, optional): The token to use for authentication. Defaults to None.
        """
        self.workspace_id = workspace_id
        self.workspace_url = get_full_workspace_api_url(workspace_id)
        if self.workspace_url is None:
            raise ValueError(
                f"Workspace {workspace_id} does not seem to exist. Did you specify the"
                " right id?"
            )
        self.token = token if token else ""

    @cached_property
    def _workspace_deployments(self):
        deployments = deployment.list_deployment(self.workspace_url, self.token)
        if isinstance(deployments, APIError):
            raise ValueError(
                f"Failed to list deployments for workspace {self.workspace_id}"
            )
        else:
            return deployments

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
        Returns:
            client: The client to call the deployment.
        """
        if deployment_name not in self._workspace_deployments_names:
            raise ValueError(
                f"Deployment {deployment_name} not found in workspace"
                f" {self.workspace_id}."
            )
        return Client(
            self.workspace_id, deployment_name, token if token else self.token
        )


class Client:
    """
    The lepton python client that calls a deployment in a workspace.

    A Client gives pythonic access to the functions defined in a deployment. For
    example, if a deployment defines two functions, `foo` and `bar`, they can
    usually be accessed via two openapi endpoint urls, `/foo` and `/bar`. The
    python equivalent will then be `client.foo` and `client.bar`, as one would
    expect a python class may have.

    The client can be initialized with a workspace id and the deployment name,
    or a full URL to the deployment's endpoint. For example, if the workspace is
    `my-workspace` and the deployment is `my-deployment`, the client can be created
    via
        client = Client("my-workspace", "my-deployment", token=MY_TOKEN)
    or if you are running locally,
        client = Client(local())
    or via a full URL if you are managing Lepton photons yourself:
        client = Client("https://my-custom-lepton-deployment.com/")
    """

    # TODO: add support for creating client with name/id
    def __init__(
        self,
        workspace_or_url: str,
        deployment: Optional[str] = None,
        token: Optional[str] = None,
    ):
        """
        Initializes a Lepton client that calls a deployment in a workspace.

        Args:
            workspace_or_url (str): The workspace id, or a full URL to the deployment's
                endpoint.
            deployment (str, optional): The deployment name. If a full URL is passed
                in, deployment can be None.
            token (str, optional): The token to use for authentication. Defaults to None.

        Implementation Note: when one uses a full URL, the client accesses the deployment
        specific endpoint directly. This endpoint may have a certain delay, and may not be
        immediately available after the deployment is created. when one uses a workspace
        id and the deployment name, the client accesses the workspace endpoint and uses
        the deployment name as a header. This is the recommended way to use the client.
        We may remove the ability to use a full URL in the future.
        """
        if _is_valid_url(workspace_or_url):
            if not _is_local_url(workspace_or_url):
                warnings.warn(
                    "Explicitly passing in a remote URL is deprecated, and may be"
                    " removed in the future. Explicitly pass in the workspace id and"
                    " deployment name instead.",
                    DeprecationWarning,
                )
            self.url = workspace_or_url
        else:
            self.url = get_full_workspace_api_url(workspace_or_url)
        self._session = requests.Session()
        if deployment is None:
            if not _is_local_url(workspace_or_url):
                warnings.warn(
                    "Remote execution without an explicit deployment is deprecated,"
                    " and may be removed in the future.",
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

    def __dir__(self) -> List[str]:
        # Note: self.paths() returns the paths with the '/' prefix, so we will
        # remove that part.
        return list(super().__dir__()) + list(p.strip("/") for p in self.paths())
