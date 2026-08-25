from pydantic import BaseModel
from requests import Response
from typing import (
    Dict,
    Optional,
    Union,
    List,
    Any,
    TypeVar,
    Type,
    NoReturn,
)


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

    _client: Any

    def __init__(self, _client: Any):
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
        """Raise ClientError or ServerError for a 4xx/5xx response."""
        if response.status_code < 400:
            return response

        response = self._response_for_diagnostic(response)
        if response.status_code < 500:
            raise ClientError(response)
        raise ServerError(response)

    @staticmethod
    def _contains_api_token_material(value: Any) -> bool:
        try:
            folded_value = str(value).casefold()
        except Exception:
            return False
        return "api_tokens" in folded_value or "apitokens" in folded_value

    def _response_for_diagnostic(self, response: Response) -> Response:
        """Return a response safe to attach to a rendered exception."""
        if not self._contains_api_token_material(response.text):
            return response

        return self._redacted_response(response)

    @staticmethod
    def _redacted_response(response: Response) -> Response:
        """Copy only status into a response with a generic diagnostic body."""
        redacted_response = Response()
        redacted_response.status_code = response.status_code
        redacted_response.encoding = "utf-8"
        redacted_response._content = (
            b"API request failed. Response details were redacted because they may"
            b" contain sensitive authentication data."
        )
        return redacted_response

    def _response_text_for_diagnostic(self, response: Response) -> str:
        return self._response_for_diagnostic(response).text

    def _format_list_item_error(self, index: int, error: Exception, item: Any) -> str:
        if self._contains_api_token_material(item) or self._contains_api_token_material(
            error
        ):
            return (
                f"\n index {index}: response item details were redacted because they"
                " may contain sensitive authentication data"
            )
        return f"\n index {index}: {error}\nitem: {item}"

    def _print_programming_error(self, response: Response, e: Exception) -> NoReturn:
        """
        Print a programming error message. This should not happen in production.
        """
        if self._contains_api_token_material(
            response.text
        ) or self._contains_api_token_material(e):
            status_code = response.status_code
            raise RuntimeError(
                "You encountered a programming error. The API returned status"
                f" {status_code}, but its response could not be decoded. Response"
                " details were redacted because they may contain sensitive"
                " authentication data."
            ) from None
        raise RuntimeError(
            "You encountered a programming error. Please report this, and include the"
            " following debug info:\n*** begin of debug info ***\nresponse returned"
            f" status {response.status_code}, but the content cannot be decoded as"
            f" json.\nresponse.text: {response.text}\n\nexception details:\n{e}\n***"
            " end of debug info ***"
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

    def ensure_list(
        self,
        response,
        EnsuredType: Type[T],
        list_key: Optional[str] = None,
    ) -> List[T]:
        """
        Ensure the response JSON is a list convertible to ``EnsuredType``.

        Args:
            response: ``requests.Response`` object.
            EnsuredType: Pydantic model class the items should map to.
            list_key: Optional key to the list in the response JSON.
        """

        self._raise_if_not_ok(response)

        valid_items = []
        errors: List[str] = []

        try:
            if list_key:
                data = response.json()
                items_raw = data.get(list_key, data) if isinstance(data, dict) else data
            else:
                items_raw = response.json()
        except Exception as e:
            self._print_programming_error(response, e)

        for idx, raw in enumerate(items_raw):
            try:
                valid_items.append(EnsuredType(**raw))
            except Exception as e:
                errors.append(self._format_list_item_error(idx, e, raw))

        if errors:
            import sys

            sys.stderr.write(
                f"[lepton-error] Skipped {len(errors)} invalid item(s) when parsing"
                " list response:"
                + "".join(errors)
                + "\n"
            )

        return valid_items

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
