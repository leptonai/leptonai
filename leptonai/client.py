import contextlib
import keyword
from typing import Callable, Dict, List, Set, Optional, Union, Iterable

from fastapi.encoders import jsonable_encoder
import httpx
from loguru import logger

from leptonai._internal.client_utils import (  # noqa
    _get_method_docstring,
    _get_positional_argument_error_message,
)
from leptonai.api.connection import Connection
from leptonai.api.workspace import (
    WorkspaceInfoLocalRecord,
    _get_full_workspace_url,
    _get_full_workspace_api_url,
)
from leptonai.config import DEFAULT_PORT
from leptonai.util import _is_valid_url
from .api import deployment, APIError


def local(port: int = DEFAULT_PORT) -> str:
    """
    Create a connection string for a local deployment. This is useful for testing
    purposes, and does not require you to type the local IP address repeatedly.

    Usage:
        client = Client(local())
        client.foo()

    Args:
        port (int, optional): The port number. Defaults to leptonai.config.DEFAULT_PORT.
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


class PathTree(object):
    def __init__(self, name: str, debug_record: List):
        self._path_cache: Dict[str, Union[Callable, PathTree]] = {}
        self._all_paths: Set[str] = set()
        self.name = name
        self.debug_record = debug_record

    def __getattr__(self, name: str) -> Union[Callable, "PathTree"]:
        try:
            return self._path_cache[name]
        except KeyError:
            raise AttributeError(
                f"No such path named {name} found. I am currently at {self.name} and"
                f" available members are ({','.join(self._path_cache.keys())})."
            )

    def __len__(self):
        return len(self._path_cache)

    def __dir__(self) -> Iterable[str]:
        return self._path_cache.keys()

    def __getitem__(self, name: str) -> Union[Callable, "PathTree"]:
        try:
            return self._path_cache[name]
        except KeyError:
            raise AttributeError(
                f"No such path named {name} found. I am currently at {self.name} and"
                f" available members are ({','.join(self._path_cache.keys())})."
            )

    def __setitem__(
        self, name: str, value: Union[Callable, "PathTree"]
    ) -> None:  # noqa
        raise NotImplementedError(
            "PathTree does not support dictionary-type set. Use add(path, func)"
            " instead."
        )

    def __call__(self):
        paths_ordered = list(self._all_paths)
        paths_ordered.sort()
        path_separator = "\n- "
        return (
            "A wrapper for leptonai Client that contains the following paths:\n"
            f"- {path_separator.join(paths_ordered)}\n"
        )

    def _has(self, path_or_name: str) -> bool:
        return path_or_name in self._all_paths or path_or_name in self._path_cache

    @staticmethod
    def rectify_name(name: str) -> str:
        """
        Rectifies the path to be a valid python identifier. For example,
        "foo/bar" will be converted to "foo_bar".
        """
        if keyword.iskeyword(name):
            name += "_"
        return name.replace("-", "_").replace(".", "_")

    # implementation note: prefixing this function with "_" in case there is
    # an api function that is called "add". Ditto for "_has" above.
    def _add(self, path: str, func: Callable):
        """
        Adds a path to the path tree. The path can contain "/"s, in which each "/"
        will be split and converted to children nodes.
        """
        if path in self._all_paths:
            self.debug_record.append(
                "Adding a path that already exists. This is not an issue of the"
                " runtime, but a deployment issue."
            )
        # Record all paths for bookkeeping purposes.
        self._all_paths.add(path)
        # Remove the leading and trailing slashes, which are not needed.
        path = path.strip("/")

        if "/" in path:
            prefix, remaining = path.split("/", 1)
            prefix = self.rectify_name(prefix)
            if prefix.isidentifier():
                if prefix not in self._path_cache:
                    self._path_cache[prefix] = PathTree(
                        (self.name + "." if self.name else "") + prefix,
                        self.debug_record,
                    )
                self._path_cache[prefix]._add(remaining, func)
            else:
                # temporarily ignore this path if it is not a valid identifier.
                # this is to prevent the case where the path is something like
                # "foo/{bar}" which we don't support yet.
                self.debug_record.append(
                    f"Path {path} is not a valid identifier. Ignoring for now."
                )
                return
        else:
            path = self.rectify_name(path)
            if path.isidentifier():
                self._path_cache[path] = func
            else:
                # temporarily ignore this path if it is not a valid identifier.
                # this is to prevent the case where the path is something like
                # "foo/{bar}" which we don't support yet.
                self.debug_record.append(
                    f"Path {path} is not a valid identifier. Ignoring for now."
                )
                return


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

    To cope with explicit urls that might have supaths, we assume that the url you
    passed in is the relative root of the deployment. This means that if you pass
    in `https://my.com/foo/bar`, the client will assume
    that there is an openapi.json file at `https://my.com/foo/bar/openapi.json`,
    and that all calls like "/function" will be relative to `https://my.com/foo/bar`,
    aka `https://my.com/foo/bar/function`.
    """

    openapi: Dict = {}

    # TODO: add support for creating client with name/id
    def __init__(
        self,
        workspace_or_url: str,
        deployment: Optional[str] = None,
        token: Optional[str] = None,
        stream: Optional[bool] = None,
        chunk_size: Optional[int] = None,
        no_check: bool = False,
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
            no_check: (bool, optional): Whether to skip checking for any errors and print
                out messages. Defaults to False.

        Implementation Note: when one uses a full URL, the client accesses the deployment
        specific endpoint directly. This endpoint may have a certain delay, and may not be
        immediately available after the deployment is created. when one uses a workspace
        id and the deployment name, the client accesses the workspace endpoint and uses
        the deployment name as a header. This is the recommended way to use the client.
        We may remove the ability to use a full URL in the future.
        """
        if _is_valid_url(workspace_or_url):
            self.url = workspace_or_url.rstrip("/")
        else:
            url = _get_full_workspace_url(workspace_or_url)
            if not url:
                raise ValueError(
                    f"Workspace {workspace_or_url} does not exist or is not accessible."
                )
            else:
                self.url = url.rstrip("/")

        headers = {}
        if deployment:
            headers.update({"X-Lepton-Deployment": deployment})
        # If we are simply using the current workspace, we will also automatically
        # set the token as the current workspace token.
        if (
            token is None
            and workspace_or_url == WorkspaceInfoLocalRecord.get_current_workspace_id()
        ):
            token = WorkspaceInfoLocalRecord.get_current_workspace_token()
        if token is not None:
            headers.update({"Authorization": f"Bearer {token}"})

        self._session = httpx.Client(headers=headers)
        self._debug_record: List = []
        self._path_cache: PathTree = PathTree("", self._debug_record)
        self.stream: Optional[bool] = stream
        self.chunk_size: Optional[int] = chunk_size

        # Check healthz to see if things are properly working
        if not self.healthz():
            self._debug_record.append(
                "Client is not healthy - healthz() returned False. This might be"
                " due to:\n- a nonstandard deployment that does not have a healthz"
                " endpoint. In this case, you may ignore this warning.\n- a network"
                " error. In this case, please check your network connection. You"
                " may want to recreate the client for things to work properly.",
            )

        # At load time, we will also load the openapi specification.
        try:
            raw_openapi = self._get("openapi.json")
            try:
                self.openapi = self._get_proper_res_content(raw_openapi)  # type: ignore
            except httpx.DecodingError:
                self._debug_record.append(
                    "OpenAPI spec failed to be json decoded. This is not an issue of"
                    " the client, but a corrupted openapi spec."
                )
        except (ConnectionError, httpx.ConnectError) as e:
            raise ConnectionError(
                "Cannot connect to server. This is not an issue of the"
                f" client, but a network error. More details:\n{e}"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                self._debug_record.append(
                    "OpenAPI spec does not exist. This is not an issue of the"
                    " client, but the deployment does not have an openapi"
                    " specification."
                )
            elif e.response.status_code == 429:
                self._debug_record.append(
                    "Server returned 429. This is not an issue of the client, but"
                    " the server is rate limiting the client. Your further requests"
                    " are likely to be rejected. Please wait for a while and try"
                    " again."
                )
            else:
                raise ConnectionError(
                    "Cannot connect to server. This is not an issue of the"
                    f" client, but a network error. More details:\n{e}"
                )
        except httpx.HTTPError:
            self._debug_record.append(
                "OpenAPI spec does not exist. This is not a client bug, but the"
                " deployment does not have an openapi specification."
            )

        # At load time, we will also set up all path caches.
        for path_name in self.paths():
            if self._path_cache._has(path_name):
                self._debug_record.append(
                    "Multiple endpoints with the same name detected. This is not an"
                    " issue of the runtime - it is caused by the deployment giving"
                    " multiple endpoints that maps to the same python name. Found"
                    " duplicated name: {path_name}."
                )
            elif path_name == "/":
                # We currently do not support a direct root path name without a
                # function name yet. Usually, "/" is a path mounted to something
                # like a swagger UI or flask service, which is not a function, so
                # we will ignore it.
                continue
            elif "post" in self.openapi["paths"][path_name]:
                self._create_post_path(path_name)
            elif "get" in self.openapi["paths"][path_name]:
                self._create_get_path(path_name)
            else:
                self._debug_record.append(
                    f"Endpoint {path_name} does not have a post or get method."
                    " Currently we only support post and get methods."
                )
        if self._debug_record and not no_check:
            logger.warning(
                "There are issues with the client. Check debug messages with "
                "`client.debug_record()`."
            )

    def __del__(self):
        self._session.close()

    # Normal usages will go through then `__getattr__` path (which triggers
    # `_post_path` and `_post`). Directly using `_post` and `_get` is
    # discouraged, only when accessing endpoints that are not defined via
    # Photon.
    def _get(self, path: str, *args, **kwargs) -> httpx.Response:
        kwargs.setdefault("timeout", None)
        if self.stream:
            return self._session.stream(
                "GET", f"{self.url}/{path.lstrip('/')}", *args, **kwargs
            )
        else:
            return self._session.get(f"{self.url}/{path.lstrip('/')}", *args, **kwargs)

    def _post(self, path: str, *args, **kwargs) -> httpx.Response:
        kwargs.setdefault("timeout", None)
        if self.stream:
            return self._session.stream(
                "POST", f"{self.url}/{path.lstrip('/')}", *args, **kwargs
            )
        else:
            return self._session.post(f"{self.url}/{path.lstrip('/')}", *args, **kwargs)

    def _generator(self, res: httpx.Response):
        ctx = res if self.stream else contextlib.nullcontext(res)
        # use context to ensure that the response is properly closed.
        with ctx as res:
            res.raise_for_status()
            if res.headers.get("content-type", None) == "application/json":
                # For a json response, we will return the json object directly,
                # as it does not make sense to stream a json object.
                res.read()
                yield False, res.json()
            if self.stream and "chunked" in res.headers.get("transfer-encoding", ""):
                yield True, None
                yield from res.iter_bytes(chunk_size=self.chunk_size)
            else:
                yield False, res.content

    def _get_proper_res_content(self, res: httpx.Response):
        content = self._generator(res)
        is_stream, non_stream_content = next(content)
        return content if is_stream else non_stream_content

    def _create_post_path(self, path_name: str) -> None:
        """
        internal method to create a method that reflects the post path.

        :param name: the name of the path. For example, if it is "https://x.lepton.ai/run", then "run" is the name used here.
        :param function_name: the name of the function.
        :return: a method that can be called to call post to the path.
        """
        if not self._path_cache._has(path_name):

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

            _method.__name__ = path_name
            if self.openapi:
                _method.__doc__ = _get_method_docstring(self.openapi, path_name)
            self._path_cache._add(path_name, _method)

    def _create_get_path(self, path_name: str) -> None:
        """
        internal method to create a method that reflects the get path.

        :param name: the name of the path. For example, if it is "https://x.lepton.ai/run",
            then "run" is the name used here.
        :param function_name: the name of the function.
        :return: a method that can be called to call get to the path.
        """
        if not self._path_cache._has(path_name):

            def _method(*args, **kwargs):
                if args:
                    raise RuntimeError(
                        _get_positional_argument_error_message(
                            self.openapi, path_name, args
                        )
                    )
                res = self._get(path_name, params=kwargs)
                return self._get_proper_res_content(res)

            _method.__name__ = path_name
            if self.openapi:
                _method.__doc__ = _get_method_docstring(self.openapi, path_name)
            self._path_cache._add(path_name, _method)

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
            self._get_proper_res_content(res)
            return True
        except (httpx.ConnectError, httpx.HTTPError):
            return False

    def debug_record(self) -> List[str]:
        print("\n\n".join(self._debug_record))
        if self._debug_record:
            print(
                "\n\nOverall, if you are the producer of the deployment, please make"
                " sure that:\n - the deployment has an openapi specification at"
                " '/openapi.json'. This is usually guaranteed if you are using the"
                " standard Photon class.\n - Also kindly ensure that every endpoint is"
                " uniquely named (note that we will try to convert '-' and '/' in URL"
                " strings to underscores).\n\nIf you are the consumer of the"
                " deployment, and do not have control over the endpoint design, a"
                " workaround is to use the `_post` method to call the endpoints"
                " directly, instead of using the pythonic utilization that the client"
                " tries to automatically provide for you."
            )

        return self._debug_record[:]  # return a copy

    def __getattr__(self, name: str):
        if len(self._path_cache) == 0:
            raise AttributeError(
                "No paths found. It is likely that the client was not initialized, or"
                " the client encountered errors during initialization time. Check the"
                " following debug messages, which contain issues during initialization:"
                "\n\n******** begin debug message ********\n"
                + "\n\n".join(self._debug_record)
                + "\n******** end debug message ********"
            )
        try:
            return self._path_cache[name]
        except KeyError:
            raise AttributeError(f"No such endpoint named {name} found.")

    def __dir__(self) -> Iterable[str]:
        return ["debug_record", "paths", "healthz", "openapi"] + list(
            self._path_cache.__dir__()
        )


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
                    "No workspace id specified, and it seems that you are not"
                    " logged in."
                )
        if (
            workspace_id == WorkspaceInfoLocalRecord.get_current_workspace_id()
            and not token
        ):
            token = WorkspaceInfoLocalRecord.get_current_workspace_token()
        self.workspace_id = workspace_id
        api_url = _get_full_workspace_api_url(workspace_id)
        if not api_url:
            raise ValueError(
                f"Workspace {workspace_id} does not seem to exist. Did you specify the"
                " right id?"
            )
        else:
            self.workspace_api_url = api_url
        self.token = token if token else ""
        self.api_conn = Connection(self.workspace_api_url, self.token)

    def _workspace_deployments(self) -> List:
        deployments = deployment.list_deployment(self.api_conn)
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
            self.workspace_id, deployment_name, token if token else self.api_conn._token
        )
