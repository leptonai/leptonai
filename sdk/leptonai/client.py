from typing import Callable, Dict, List, Optional
from urllib.parse import urljoin
import warnings

from fastapi.encoders import jsonable_encoder
import requests

from leptonai._internal.client_utils import (
    _is_valid_url,
    _is_local_url,
    _get_method_docstring,
    _get_positional_argument_error_message,
    _fallback_api_call_message,
)
from leptonai.api.connection import Connection
from leptonai.api.workspace import (
    WorkspaceInfoLocalRecord,
    _get_full_workspace_url,
    _get_full_workspace_api_url,
)
from .api import deployment, APIError


def local(port: int = 8080) -> str:
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


def current() -> str:
    """
    Returns the current workspace id. This is useful for creating a client that
    calls deployments in the current workspace. Note that when instantiating a
    client, if the current workspace is used, the token will be automatically
    set to the current workspace token if not specified.
    """
    id = WorkspaceInfoLocalRecord.get_current_workspace_id()
    if id is None:
        raise RuntimeError("No current workspace is set.")
    return id


class Client(object):
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

    _path_cache: Dict[str, Callable] = {}
    openapi: Dict = {}

    # TODO: add support for creating client with name/id
    def __init__(
        self,
        workspace_or_url: str,
        deployment: Optional[str] = None,
        token: Optional[str] = None,
        stream: Optional[bool] = None,
        chunk_size: Optional[int] = None,
    ):
        """
        Initializes a Lepton client that calls a deployment in a workspace.

        Args:
            workspace_or_url (str): The workspace id, or a full URL to the deployment's
                endpoint. Use `local()` to access a local deployment, and `current()`
                to access the current workspace if you have logged in.
            deployment (str, optional): The deployment name. If a full URL is passed
                in, deployment can be None.
            token (str, optional): The token to use for authentication. Defaults to None.
            stream (bool, optional): Whether to stream the response. Defaults to None.
                Note that if stream is specified but the return type is json, we will
                still return the json object lump sum, instead of a generator.
            chunk_size (int, optional): The chunk size to use when streaming. Defaults to None.

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
                    " removed in the future. Explicitly pass in the workspace id"
                    " and deployment name instead.",
                    DeprecationWarning,
                )
            self.url = workspace_or_url
        else:
            url = _get_full_workspace_url(workspace_or_url)
            if not url:
                raise ValueError(
                    f"Workspace {workspace_or_url} does not exist or is not accessible."
                )
            else:
                self.url = url
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
        # If we are simply using the current workspace, we will also automatically
        # set the token as the current workspace token.
        if (
            token is None
            and workspace_or_url == WorkspaceInfoLocalRecord.get_current_workspace_id()
        ):
            token = WorkspaceInfoLocalRecord._get_current_workspace_token()
        if token is not None:
            self._session.headers.update({"Authorization": f"Bearer {token}"})
        self._path_cache = {}
        self.stream = stream
        self.chunk_size = chunk_size

        # Check healthz to see if things are properly working
        if not self.healthz():
            warnings.warn(
                "Client is not healthy - healthz() returned False. This might be"
                " due to:\n- a nonstandard deployment that does not have a healthz"
                " endpoint. In this case, you may ignore this warning.\n- a network"
                " error. In this case, please check your network connection. You"
                " may want to recreate the client for things to work properly.",
                RuntimeWarning,
            )

        # At load time, we will also load the openapi specification.
        try:
            raw_openapi = self._get("/openapi.json")
            raw_openapi.raise_for_status()
            try:
                self.openapi = raw_openapi.json()
            except requests.JSONDecodeError:
                warnings.warn(
                    "OpenAPI spec failed to be json decoded. This is not an issue of"
                    " the client, but a corrupted openapi spec.\n\n"
                    + _fallback_api_call_message,
                    RuntimeWarning,
                )
        except (ConnectionError, requests.ConnectionError) as e:
            raise ConnectionError(
                "Cannot connect to server. This is not an issue of the"
                f" client, but a network error. More details:\n\n{e}"
            )
        except requests.HTTPError:
            warnings.warn(
                "OpenAPI spec does not exist. This is not a client bug, but the"
                " deployment does not have an openapi specification.\n\n"
                + _fallback_api_call_message,
                RuntimeWarning,
            )

        # At load time, we will also set up all path caches.
        for path_name in self.paths():
            function_name = path_name[1:] if path_name.startswith("/") else path_name
            # Replace the slashes and dashes in function_name with underscore
            # to make it a valid python function name.
            function_name = function_name.replace("/", "_").replace("-", "_")
            if function_name in self._path_cache:
                warnings.warn(
                    "Multiple endpoints with the same name detected. This is not"
                    " an issue of the runtime - it is caused by the deployment giving"
                    " multiple endpoints that maps to the same python name.\n\n"
                    + _fallback_api_call_message
                    + f"\n\ndebug info: found duplicated name {path_name}.",
                    RuntimeWarning,
                )
                # For the sake of avoiding confusions, we will clear the path cache.
                self._path_cache = {}
                break
            if "post" in self.openapi["paths"][path_name]:
                self._post_path(path_name, function_name)
            elif "get" in self.openapi["paths"][path_name]:
                self._get_path(path_name, function_name)
            else:
                warnings.warn(
                    f"Endpoint {path_name} does not have a post or get method."
                    " Currently we only support post and get methods.\n\n"
                    + _fallback_api_call_message,
                    RuntimeWarning,
                )

    # Normal usages will go through then `__getattr__` path (which triggers
    # `_post_path` and `_post`). Directly using `_post` and `_get` is
    # discouraged, only when accessing endpoints that are not defined via
    # Photon.
    def _get(self, path: str, *args, **kwargs) -> requests.models.Response:
        return self._session.get(
            urljoin(self.url, path), stream=self.stream, *args, **kwargs
        )

    def _post(self, path: str, *args, **kwargs) -> requests.models.Response:
        return self._session.post(
            urljoin(self.url, path), stream=self.stream, *args, **kwargs
        )

    def _get_proper_res_content(self, res: requests.models.Response):
        res.raise_for_status()
        if res.headers.get("content-type", None) == "application/json":
            return res.json()
        else:
            if self.stream and "chunked" in res.headers.get("transfer-encoding", ""):
                return res.iter_content(chunk_size=self.chunk_size)
            else:
                return res.content

    def _post_path(self, path_name: str, function_name: str) -> Callable:
        """
        internal method to create a method that reflects the post path.

        :param name: the name of the path. For example, if it is "https://x.lepton.ai/run", then "run" is the name used here.
        :param function_name: the name of the function.
        :return: a method that can be called to call post to the path.
        """
        if function_name not in self._path_cache:

            def _method(*args, **kwargs):
                if args:
                    raise RuntimeError(
                        _get_positional_argument_error_message(
                            self.openapi, path_name, args
                        )
                    )
                res = self._post(
                    path_name,
                    json=jsonable_encoder(kwargs),
                )
                return self._get_proper_res_content(res)

            _method.__name__ = function_name
            if self.openapi:
                _method.__doc__ = _get_method_docstring(self.openapi, path_name)
            self._path_cache[function_name] = _method
        return self._path_cache[function_name]

    def _get_path(self, path_name: str, function_name: str) -> Callable:
        """
        internal method to create a method that reflects the get path.

        :param name: the name of the path. For example, if it is "https://x.lepton.ai/run",
            then "run" is the name used here.
        :param function_name: the name of the function.
        :return: a method that can be called to call get to the path.
        """
        if function_name not in self._path_cache:

            def _method(*args, **kwargs):
                if args:
                    raise RuntimeError(
                        _get_positional_argument_error_message(
                            self.openapi, path_name, args
                        )
                    )
                res = self._get(path_name, params=kwargs)
                return self._get_proper_res_content(res)

            _method.__name__ = function_name
            if self.openapi:
                _method.__doc__ = _get_method_docstring(self.openapi, path_name)
            else:
                _method.__doc__ = ""
            self._path_cache[function_name] = _method
        return self._path_cache[function_name]

    def paths(self) -> List[str]:
        """
        Returns a list of paths that are defined in the openapi specification.
        If the openapi specification does not exist, returns an empty list.

        :return: a list of paths, each of which is a string.
        """
        if "paths" in self.openapi:
            return self.openapi["paths"].keys()
        return []

    def healthz(self) -> bool:
        """
        Returns whether the deployment is healthily running. Note that this function
        relies on the server side to expose the "/healthz" endpoint. Some deployments
        such as the flask and gradio mounted deployments may not have this endpoint,
        so you should treat the return value of this function as a hint, not a
        guarantee.

        :return: whether the deployment is healthily running.
        """
        try:
            res = self._get("/healthz")
            res.raise_for_status()
            return True
        except (requests.ConnectionError, requests.HTTPError):
            return False

    def __getattr__(self, name: str):
        try:
            return self._path_cache[name]
        except KeyError:
            raise AttributeError(f"No such endpoint named {name} found.")

    def __dir__(self):
        return self._path_cache.keys()


class Workspace(object):
    """
    The lepton python class that holds necessary info to access a workspace.

    A workspace allows one to access a set of deployments under this workspace.
    Currently, we do not support local workspaces - all workspaces are remote.
    """

    def __init__(self, workspace_id: Optional[str] = None, token: Optional[str] = None):
        """
        Creates a Lepton workspace.

        Args:
            workspace_id (str): The workspace id. If not specified, the currently
                logged in workspace will be used.
            token (str, optional): The token to use for authentication. Defaults to None.
        """
        if workspace_id is None:
            workspace_id = WorkspaceInfoLocalRecord.get_current_workspace_id()
            if workspace_id is None:
                raise ValueError(
                    "No workspace id specified, and no current workspace is set."
                )
            token = WorkspaceInfoLocalRecord._get_current_workspace_token()
        self.workspace_id = workspace_id
        api_url = _get_full_workspace_api_url(workspace_id)
        if not api_url:
            raise ValueError(
                f"Workspace {workspace_id} does not seem to exist. Did you specify the"
                " right id?"
            )
        self.conn = Connection(api_url, token)

    def _workspace_deployments(self) -> List:
        deployments = deployment.list_deployment(self.conn)
        if isinstance(deployments, APIError):
            raise ValueError(
                f"Failed to list deployments for workspace {self.workspace_id}"
            )
        else:
            return deployments

    def list_deployments(self) -> List[str]:
        return [deployment["name"] for deployment in self._workspace_deployments()]

    def client(self, deployment_name: str, token: Optional[str] = None) -> Client:
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
        if deployment_name not in self.list_deployments():
            raise ValueError(
                f"Deployment {deployment_name} not found in workspace"
                f" {self.workspace_id}."
            )
        return Client(
            self.workspace_id, deployment_name, token if token else self.conn._token
        )
