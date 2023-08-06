from typing import Callable, Dict, List, Optional
from urllib.parse import urljoin, urlparse
import warnings

from backports.cached_property import cached_property
from fastapi.encoders import jsonable_encoder
import requests

from leptonai.api.workspace import get_full_workspace_url, get_full_workspace_api_url
from .api import deployment, APIError


def _is_valid_url(candidate_str: str) -> bool:
    parsed = urlparse(candidate_str)
    return parsed.scheme != "" and parsed.netloc != ""


def _is_local_url(candidate_str: str) -> bool:
    parsed = urlparse(candidate_str)
    local_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
    return parsed.netloc.lower() in local_hosts


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


def _json_to_type_string(schema: Dict) -> str:
    """
    Internal util function to convert a json to a type string.
    """
    if "type" in schema:
        if "items" in schema:
            # items defines the type of items in an array.
            typestr = f"{schema['type']}[{_json_to_type_string(schema['items'])}]"
        elif "prefixItems" in schema:
            # repeateditems defines the type of the first few items in an array, and
            # then the min and max of the array.
            min_items = schema.get("minItems", "?")
            max_items = schema.get("maxItems", "?")
            typestr = (
                f"{schema['type']}[{', '.join(_json_to_type_string(x) for x in schema['prefixItems'])},"
                f" ...] (min={min_items},max={max_items})"
            )
        else:
            typestr = schema["type"]
    elif "anyOf" in schema:
        typestr = f"({' | '.join(_json_to_type_string(x) for x in schema['anyOf'])})"
    else:
        # If we have no idea waht the type is, we will just return "Any".
        typestr = "Any"
    if "default" in schema:
        typestr += f" (default: {schema['default']})"
    return typestr


def _get_method_docstring(openapi: Dict, path_name: str) -> str:
    """
    Get the docstring for a method from the openapi specification.
    """
    is_post = False
    try:
        api_info = openapi["paths"][f"{path_name}"]["post"]
        is_post = True
    except KeyError:
        # No path or post info exists: this is probably a get method.
        try:
            api_info = openapi["paths"][f"{path_name}"]["get"]
        except KeyError:
            # No path or get info exists: we will just return an empty docstring.
            return ""

    # Add description to docstring. We will use the description, and if not,
    # the summary as a backup plan, and if not, we will not add a docstring.
    docstring = api_info.get("description", api_info.get("summary", ""))

    if not is_post:
        # TODO: add support to parse get methods' parameters.
        return docstring

    docstring += "\n\nAutomatically inferred parameters from openapi:"
    # Add schema to the docstring.
    try:
        schema_ref = api_info["requestBody"]["content"]["application/json"]["schema"][
            "$ref"
        ]
        schema_name = schema_ref.split("/")[-1]
        schema = openapi["components"]["schemas"][schema_name]
        schema_strings = [
            (k, _json_to_type_string(v)) for k, v in schema["properties"].items()
        ]
        if len(schema_strings) == 0:
            docstring += "\n\nInput Schema: None"
        elif "required" in schema:
            # We will sort the schema strings to make required fields appear first
            schema_strings = sorted(
                schema_strings, key=lambda x: x[0] in schema["required"], reverse=True
            )
            docstring += "\n\nInput Schema (*=required):\n  " + "\n  ".join(
                [
                    f"{k}{'*' if k in schema['required'] else ''}: {v}"
                    for k, v in schema_strings
                ]
            )
        else:
            docstring += "\n\nSchema:\n  " + "\n  ".join(
                [f"{k}: {v}" for k, v in schema_strings]
            )
    except KeyError:
        # If the openapi does not have a schema section, we will just skip.
        pass

    # Add example input to the docstring if existing.
    try:
        example = api_info["requestBody"]["content"]["application/json"]["example"]
        example_string = "\n  ".join(
            [str(k) + ": " + str(v) for k, v in example.items()]
        )
        docstring += f"\n\nExample input:\n  {example_string}\n"
    except KeyError:
        # If the openapi does not have an example section, we will just skip.
        pass

    # Add output schema to the docstring.
    try:
        schema_ref = api_info["responses"]["200"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        schema_name = schema_ref.split("/")[-1]
        schema = openapi["components"]["schemas"][schema_name]
        schema_strings = [
            (k, _json_to_type_string(v)) for k, v in schema["properties"].items()
        ]
        docstring += "\n\nOutput Schema:\n  " + "\n  ".join(
            [f"{k}: {v}" for k, v in schema_strings]
        )
    except KeyError:
        # If the openapi does not have a schema section, we will just skip.
        pass

    return docstring


_fallback_api_call_message = (
    "If you are the producer of the deployment, please make sure that the deployment"
    " has an openapi specification at '/openapi.json'. This is usually guaranteed if"
    " you are using the standard Photon class. Also kindly ensure that every endpoint"
    " is uniquely named (note that we will try to convert '-' and '/' in URL strings to"
    " underscores). If you are the consumer of the deployment, and do not have control"
    " over the endpoint design, a workaround is to use the `_post` method to call the"
    " endpoints directly, instead of using the pythonic method name."
)


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
    openapi: Optional[Dict] = None

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
            self._session.headers.update({"X-Lepton-Deployment": deployment})
        if token is not None:
            self._session.headers.update({"Authorization": f"Bearer {token}"})
        self._path_cache = {}

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
        except requests.ConnectionError as e:
            raise requests.ConnectionError(
                "Cannot connect to server for openapi.json. This is not an issue of the"
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
            function_name = path_name.strip("/")
            # Replace the slashes and dashes in function_name with underscore
            # to make it a valid python function name.
            function_name = function_name.replace("/", "_").replace("-", "_")
            if function_name in self._path_cache:
                warnings.warn(
                    "Multiple endpoints with the same name detected. This is not"
                    " an issue of the runtime - it is caused by the deployment giving"
                    " multiple endpoints that maps to the same python name.\n\n"
                    + _fallback_api_call_message,
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
        return self._session.get(urljoin(self.url, path), *args, **kwargs)

    def _post(self, path: str, *args, **kwargs) -> requests.models.Response:
        return self._session.post(urljoin(self.url, path), *args, **kwargs)

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
                        "Photon methods do not support positional arguments - did you"
                        " forget to pass in a keyword argument?"
                    )
                res = self._post(
                    path_name,
                    json=jsonable_encoder(kwargs),
                )
                res.raise_for_status()
                return res.json()

            _method.__name__ = function_name
            if self.openapi:
                _method.__doc__ = _get_method_docstring(self.openapi, path_name)
            self._path_cache[function_name] = _method
        return self._path_cache[function_name]

    def _get_path(self, path_name: str, function_name: str) -> Callable:
        """
        internal method to create a method that reflects the get path.

        :param name: the name of the path. For example, if it is "https://x.lepton.ai/run", then "run" is the name used here.
        :param function_name: the name of the function.
        :return: a method that can be called to call get to the path.
        """
        if function_name not in self._path_cache:

            def _method(*args, **kwargs):
                if args:
                    raise RuntimeError(
                        "Photon methods do not support positional arguments - did you"
                        " forget to pass in a keyword argument?"
                    )
                res = self._get(path_name, params=kwargs)
                res.raise_for_status()
                return res.json()

            _method.__name__ = function_name
            if self.openapi:
                _method.__doc__ = _get_method_docstring(self.openapi, path_name)
            self._path_cache[function_name] = _method
        return self._path_cache[function_name]

    def paths(self) -> List[str]:
        """
        Returns a list of paths that are defined in the openapi specification.
        If the openapi specification does not exist, returns an empty list.

        :return: a list of paths, each of which is a string.
        """
        if self.openapi is not None:
            return self.openapi["paths"].keys()
        return []

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
    def _workspace_deployments(self) -> List:
        deployments = deployment.list_deployment(self.workspace_url, self.token)
        if isinstance(deployments, APIError):
            raise ValueError(
                f"Failed to list deployments for workspace {self.workspace_id}"
            )
        else:
            return deployments

    @cached_property
    def _workspace_deployments_names(self) -> List[str]:
        return [deployment["name"] for deployment in self._workspace_deployments]

    def list_deployments(self) -> List:
        """
        List all deployments on this workspace.
        """
        return self._workspace_deployments_names

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
        if deployment_name not in self._workspace_deployments_names:
            raise ValueError(
                f"Deployment {deployment_name} not found in workspace"
                f" {self.workspace_id}."
            )
        return Client(
            self.workspace_id, deployment_name, token if token else self.token
        )
