from pydantic import BaseModel
from typing import TYPE_CHECKING, Dict, Union, List, Any, TypeVar, Type

if TYPE_CHECKING:
    # only used for type hinting, but avoids circular imports
    from .workspace import Workspace


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

    _ws: "Workspace"

    def __init__(self, ws: "Workspace"):
        """
        Initializes the APIResource with the Workspace object. You should not
        need to explicitly call this method. All APIResource classes should
        be initialized by the Workspace object in the Workspace class's __init__
        function.
        """
        self._ws = ws
        self._get = ws._get
        self._post = ws._post
        self._put = ws._put
        self._patch = ws._patch
        self._delete = ws._delete
        self._head = ws._head

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

    T = TypeVar("T", bound=BaseModel)

    def ensure_type(self, response, EnsuredType: Type[T]) -> T:
        """
        Utility function to ensure that the response is of the given type.
        """
        if not response.ok:
            raise RuntimeError(
                f"API call failed with status code {response.status_code}. Details:"
                f" {response.text}"
            )
        try:
            return EnsuredType(**response.json())
        except Exception as e:
            # This should not happen: apis that use json_or_error should make sure
            # that the response is json. If this happens, it is either a programming
            # error, or the api has changed, or the lepton ai cloud side has a bug.
            raise RuntimeError(
                "You encountered a programming error. Please report this, and include"
                " the following debug info:\n*** begin of debug info ***\nresponse"
                " returned 200 OK, but the content cannot be decoded as"
                f" json.\nresponse.text: {response.text}\n\nexception"
                f" details:\n{e}\n*** end of debug info ***"
            )

    def ensure_list(self, response, EnsuredType: Type[T]) -> List[T]:
        """
        Utility function to ensure that the response is a list of the given type.
        """
        if not response.ok:
            raise RuntimeError(
                f"API call failed with status code {response.status_code}. Details:"
                f" {response.text}"
            )
        try:
            return [EnsuredType(**item) for item in response.json()]
        except Exception as e:
            # This should not happen: apis that use json_or_error should make sure
            # that the response is json. If this happens, it is either a programming
            # error, or the api has changed, or the lepton ai cloud side has a bug.
            raise RuntimeError(
                "You encountered a programming error. Please report this, and include"
                " the following debug info:\n*** begin of debug info ***\nresponse"
                " returned 200 OK, but the content cannot be decoded as"
                f" json.\nresponse.text: {response.text}\n\nexception"
                f" details:\n{e}\n*** end of debug info ***"
            )

    def ensure_ok(self, response) -> bool:
        """
        Utility function to ensure that the response is ok.
        """
        if not response.ok:
            raise RuntimeError(
                f"API call failed with status code {response.status_code}. Details:"
                f" {response.text}"
            )
        return True

    def ensure_json(self, response) -> Union[Dict, List, str]:
        """
        Utility function to ensure that the output is a json object (including dict, list, etc.)
        """
        if not response.ok:
            raise RuntimeError(
                f"API call failed with status code {response.status_code}. Details:"
                f" {response.text}"
            )
        try:
            return response.json()
        except Exception as e:
            # This should not happen: apis that use json_or_error should make sure
            # that the response is json. If this happens, it is either a programming
            # error, or the api has changed, or the lepton ai cloud side has a bug.
            raise RuntimeError(
                "You encountered a programming error. Please report this, and include"
                " the following debug info:\n*** begin of debug info ***\nresponse"
                " returned 200 OK, but the content cannot be decoded as"
                f" json.\nresponse.text: {response.text}\n\nexception"
                f" details:\n{e}\n*** end of debug info ***"
            )
