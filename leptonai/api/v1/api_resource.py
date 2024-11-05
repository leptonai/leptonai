from pydantic import BaseModel
from requests import Response
from typing import TYPE_CHECKING, Dict, Union, List, Any, TypeVar, Type, NoReturn

if TYPE_CHECKING:
    # only used for type hinting, but avoids circular imports
    from .client import APIClient


class ClientError(RuntimeError):
    def __init__(self, response: Response):
        super().__init__(
            f"Client error during API call: {response.status_code} {response.text}"
        )
        self.response = response


class ServerError(RuntimeError):
    def __init__(self, response: Response):
        super().__init__(
            f"Server error during API call: {response.status_code} {response.text}"
        )
        self.response = response


class APIResourse(object):
    """
    APIResource is a base class for all api implementations. It is registered
    with the Workspace object and provides a set of utility functions to
    interact with the API. For example, for all deployment related operations,
    the DeploymentAPI class is used which is a subclass of APIResource.

    Implementation note: if you are implementing a new set of API, you should subclass
    APIResource and implement the required methods. And then, in leptonai/api/v1/workspace.py,
    you should add a new line in the __init__ function to register the new APIResource.
    For example, if you are implementing a new API for "Magic", you should define a
    class MagicAPI(APIResource) and then in the __init__ function of Workspace, you should
    add the following line:
        self.magic = MagicAPI(self)
    See for example leptonai/api/v1/deployment.py for an example.
    """

    _client: "APIClient"

    def __init__(self, _client: "APIClient"):
        """
        Initializes the APIResource with the Workspace object. You should not
        need to explicitly call this method. All APIResource classes should
        be initialized by the Workspace object in the Workspace class's __init__
        function.
        """
        self._client = _client
        self._get = _client._get
        self._post = _client._post
        self._put = _client._put
        self._patch = _client._patch
        self._delete = _client._delete
        self._head = _client._head

    # A type variable to represent a subclass of BaseModel
    T = TypeVar("T", bound=BaseModel)

    def safe_json(
        self, content: Union[T, List[T]]
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        A utility function to safely convert BaseModel or a list of BaseModel to
        JSON serializable dictionary or list of dictionary. This also honors the alias
        defined in the BaseModel.

        Args:
            content (Union[T, List[T]]): BaseModel or List[BaseModel]
        Returns:
            Union[Dict[str, Any], List[Dict[str, Any]]]: JSON serializable dictionary
            or list of dictionary
        Raises:
            ValueError: If the input is not BaseModel or List[BaseModel]
        """
        if isinstance(content, BaseModel):
            return content.dict(exclude_none=True, by_alias=True)
        elif isinstance(content, list) and all(
            isinstance(c, BaseModel) for c in content
        ):
            return [c.dict(exclude_none=True, by_alias=True) for c in content]
        else:
            raise ValueError(
                "safe_json only accepts BaseModel or List[BaseModel] as input."
            )

    def _raise_if_not_ok(self, response: Response):
        """
        Raise a RuntimeError if the response is not ok. Given the
        """
        if response.status_code >= 400 and response.status_code < 500:
            raise ClientError(response)
        elif response.status_code >= 500:
            raise ServerError(response)
        return response

    def _print_programming_error(self, response: Response, e: Exception) -> NoReturn:
        """
        Print a programming error message. This should not happen in production.
        """
        raise RuntimeError(
            "You encountered a programming error. Please report this, and include"
            " the following debug info:\n*** begin of debug info ***\nresponse"
            " returned 200 OK, but the content cannot be decoded as"
            f" json.\nresponse.text: {response.text}\n\nexception"
            f" details:\n{e}\n*** end of debug info ***"
        )

    T = TypeVar("T", bound=BaseModel)

    def ensure_type(self, response, EnsuredType: Type[T]) -> T:
        """
        Utility function to ensure that the response is of the given type.
        """
        self._raise_if_not_ok(response)
        try:
            return EnsuredType(**response.json())
        except Exception as e:
            self._print_programming_error(response, e)

    def ensure_list(self, response, EnsuredType: Type[T]) -> List[T]:
        """
        Utility function to ensure that the response is a list of the given type.
        """
        self._raise_if_not_ok(response)
        try:
            return [EnsuredType(**item) for item in response.json()]
        except Exception as e:
            self._print_programming_error(response, e)

    def ensure_ok(self, response) -> bool:
        """
        Utility function to ensure that the response is ok.
        """
        self._raise_if_not_ok(response)
        return True

    def ensure_json(self, response: Response) -> Any:
        """
        Utility function to ensure that the output is a json object (including dict, list, etc.)
        """
        self._raise_if_not_ok(response)
        try:
            return response.json()
        except Exception as e:
            self._print_programming_error(response, e)
