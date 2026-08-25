import json

from pydantic import BaseModel, ValidationError
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

    _REDACTED_DIAGNOSTIC = (
        "API request failed. Response details were redacted because they may contain"
        " sensitive authentication data."
    )
    _REDACTED_API_TOKEN_DIAGNOSTIC = (
        "API request failed and the response referenced api_tokens. Raw response"
        " details were redacted because they could contain credential material."
    )
    _SAFE_DIAGNOSTIC_HEADERS = frozenset({
        "date",
        "retry-after",
        "traceparent",
        "x-amzn-requestid",
        "x-correlation-id",
        "x-lepton-request-id",
        "x-request-id",
    })

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

    @staticmethod
    def _normalized_field_name(value: Any) -> str:
        return str(value).replace("_", "").casefold()

    @classmethod
    def _is_api_token_field(cls, value: Any) -> bool:
        return cls._normalized_field_name(value) == "apitokens"

    @classmethod
    def _has_api_token_field(cls, value: Any) -> bool:
        if isinstance(value, dict):
            return any(
                cls._is_api_token_field(key) or cls._has_api_token_field(child)
                for key, child in value.items()
            )
        if isinstance(value, list):
            return any(cls._has_api_token_field(child) for child in value)
        return False

    @classmethod
    def _has_misplaced_api_token_field(
        cls,
        value: Any,
        *,
        path: tuple = (),
    ) -> bool:
        """Whether a token field occurs outside canonical ``spec.api_tokens``."""
        if isinstance(value, dict):
            for key, child in value.items():
                field_name = cls._normalized_field_name(key)
                if cls._is_api_token_field(key) and path != ("spec",):
                    return True
                if cls._has_misplaced_api_token_field(
                    child,
                    path=(*path, field_name),
                ):
                    return True
        elif isinstance(value, list):
            return any(
                cls._has_misplaced_api_token_field(child, path=path) for child in value
            )
        return False

    @classmethod
    def _api_token_literal_values(cls, value: Any) -> List[str]:
        """Collect literal credentials from snake/camel-case token containers."""
        values: List[str] = []

        def collect_value_strings(item: Any) -> None:
            if isinstance(item, str):
                if item and item != "***":
                    values.append(item)
            elif isinstance(item, dict):
                for child in item.values():
                    collect_value_strings(child)
            elif isinstance(item, list):
                for child in item:
                    collect_value_strings(child)

        def visit(
            item: Any,
            *,
            in_token_container: bool = False,
            direct_scalar_is_token: bool = False,
        ) -> None:
            if isinstance(item, dict):
                for key, child in item.items():
                    field_name = cls._normalized_field_name(key)
                    if cls._is_api_token_field(key):
                        visit(
                            child,
                            in_token_container=True,
                            direct_scalar_is_token=True,
                        )
                    elif in_token_container and field_name == "valuefrom":
                        # A secret reference names a server-side object; it is not a
                        # literal credential and remains useful in diagnostics.
                        continue
                    elif in_token_container and field_name == "value":
                        collect_value_strings(child)
                    else:
                        visit(
                            child,
                            in_token_container=in_token_container,
                            direct_scalar_is_token=False,
                        )
            elif isinstance(item, list):
                for child in item:
                    visit(
                        child,
                        in_token_container=in_token_container,
                        direct_scalar_is_token=direct_scalar_is_token,
                    )
            elif (
                in_token_container
                and direct_scalar_is_token
                and isinstance(item, str)
                and item != "***"
            ):
                values.append(item)

        visit(value)
        return values

    @classmethod
    def _redact_api_token_fields(
        cls,
        value: Any,
        *,
        in_token_container: bool = False,
        direct_scalar_is_token: bool = False,
    ) -> Any:
        """Return JSON-compatible data with literal token values replaced."""
        if isinstance(value, dict):
            redacted = {}
            for key, child in value.items():
                field_name = cls._normalized_field_name(key)
                if cls._is_api_token_field(key):
                    redacted[key] = cls._redact_api_token_fields(
                        child,
                        in_token_container=True,
                        direct_scalar_is_token=True,
                    )
                elif in_token_container and field_name == "valuefrom":
                    redacted[key] = child
                elif in_token_container and field_name == "value":
                    redacted[key] = "***" if child else child
                else:
                    redacted[key] = cls._redact_api_token_fields(
                        child,
                        in_token_container=in_token_container,
                        direct_scalar_is_token=False,
                    )
            return redacted
        if isinstance(value, list):
            return [
                cls._redact_api_token_fields(
                    child,
                    in_token_container=in_token_container,
                    direct_scalar_is_token=direct_scalar_is_token,
                )
                for child in value
            ]
        if (
            in_token_container
            and direct_scalar_is_token
            and isinstance(value, str)
            and value
        ):
            return "***"
        return value

    @staticmethod
    def _redact_sensitive_values(text: str, sensitive_values) -> str:
        redacted = text
        values = {
            value
            for value in sensitive_values or []
            if isinstance(value, str) and value and value != "***"
        }
        representations = set(values)
        for value in values:
            representations.add(json.dumps(value)[1:-1])
            representations.add(json.dumps(value, ensure_ascii=False)[1:-1])
            representations.add(repr(value)[1:-1])
        for representation in sorted(representations, key=len, reverse=True):
            redacted = redacted.replace(representation, "***")
        return redacted

    @classmethod
    def _safe_exception_text(cls, error: Exception, sensitive_values=None) -> str:
        """Format an exception without Pydantic's potentially truncated input repr."""
        if isinstance(error, ValidationError):
            details = []
            for validation_error in error.errors(
                include_url=False,
                include_input=False,
            ):
                location = ".".join(
                    str(part) for part in validation_error.get("loc", ())
                )
                message = validation_error.get("msg", "validation failed")
                error_type = validation_error.get("type", "validation_error")
                details.append(f"{location or '<root>'}: {message} [type={error_type}]")
            count = error.error_count()
            label = "error" if count == 1 else "errors"
            text = f"{count} validation {label}\n" + "\n".join(details)
        else:
            text = str(error)
        return cls._redact_sensitive_values(text, sensitive_values)

    @classmethod
    def _redact_sensitive_values_in_data(cls, value: Any, sensitive_values) -> Any:
        """Redact decoded JSON strings before they are escaped for diagnostics."""
        if isinstance(value, dict):
            return {
                (
                    cls._redact_sensitive_values(key, sensitive_values)
                    if isinstance(key, str)
                    else key
                ): cls._redact_sensitive_values_in_data(child, sensitive_values)
                for key, child in value.items()
            }
        if isinstance(value, list):
            return [
                cls._redact_sensitive_values_in_data(child, sensitive_values)
                for child in value
            ]
        if isinstance(value, str):
            return cls._redact_sensitive_values(value, sensitive_values)
        return value

    @classmethod
    def _response_with_diagnostic_body(
        cls,
        response: Response,
        body: str,
        *,
        preserve_content_type: bool = False,
    ) -> Response:
        """Copy allowlisted response metadata without retaining request secrets."""
        diagnostic = Response()
        diagnostic.status_code = response.status_code
        diagnostic.encoding = response.encoding or "utf-8"
        diagnostic.url = response.url
        diagnostic.reason = response.reason
        diagnostic.elapsed = response.elapsed
        for name, value in response.headers.items():
            if name.casefold() in cls._SAFE_DIAGNOSTIC_HEADERS:
                diagnostic.headers[name] = value
        if preserve_content_type and "Content-Type" in response.headers:
            diagnostic.headers["Content-Type"] = response.headers["Content-Type"]
        diagnostic._content = body.encode(diagnostic.encoding, errors="replace")
        return diagnostic

    def _response_for_diagnostic(
        self,
        response: Response,
        *,
        sensitive_values=None,
    ) -> Response:
        """Return a response whose body is safe to attach to an exception."""
        known_values = list(sensitive_values or [])
        must_detach_request = bool(known_values)
        parsed = None
        try:
            parsed = response.json()
        except Exception:
            pass

        if parsed is not None:
            has_token_field = self._has_api_token_field(parsed)
            known_values.extend(self._api_token_literal_values(parsed))
            redacted_payload = self._redact_api_token_fields(parsed)
            redacted_payload = self._redact_sensitive_values_in_data(
                redacted_payload,
                known_values,
            )
            if not has_token_field and self._contains_api_token_material(
                redacted_payload
            ):
                return self._response_with_diagnostic_body(
                    response,
                    self._REDACTED_API_TOKEN_DIAGNOSTIC,
                )
            if redacted_payload != parsed:
                body = json.dumps(redacted_payload)
            else:
                body = response.text
        else:
            body = response.text

        body = self._redact_sensitive_values(body, known_values)
        if body == response.text:
            if parsed is None and self._contains_api_token_material(body):
                return self._response_with_diagnostic_body(
                    response,
                    self._REDACTED_API_TOKEN_DIAGNOSTIC,
                )
            if must_detach_request:
                return self._response_with_diagnostic_body(
                    response,
                    body,
                    preserve_content_type=True,
                )
            return response

        return self._response_with_diagnostic_body(response, body)

    @classmethod
    def _redacted_response(cls, response: Response) -> Response:
        """Return a generic body while retaining only safe response metadata."""
        return cls._response_with_diagnostic_body(
            response,
            cls._REDACTED_DIAGNOSTIC,
        )

    def _response_text_for_diagnostic(self, response: Response) -> str:
        return self._response_for_diagnostic(response).text

    def _format_list_item_error(self, index: int, error: Exception, item: Any) -> str:
        literal_values = self._api_token_literal_values(item)
        safe_error = self._safe_exception_text(error, literal_values)
        safe_item = self._redact_api_token_fields(item)
        return f"\n index {index}: {safe_error}\nitem: {safe_item}"

    def _print_programming_error(self, response: Response, e: Exception) -> NoReturn:
        """
        Print a programming error message. This should not happen in production.
        """
        literal_values = []
        try:
            literal_values = self._api_token_literal_values(response.json())
        except Exception:
            pass
        diagnostic_response = self._response_for_diagnostic(
            response,
            sensitive_values=literal_values,
        )
        safe_error = self._safe_exception_text(e, literal_values)
        raise RuntimeError(
            "You encountered a programming error. Please report this, and include the"
            " following debug info:\n*** begin of debug info ***\nresponse returned"
            f" status {diagnostic_response.status_code}, but the content cannot be"
            " decoded as"
            f" json.\nresponse.text: {diagnostic_response.text}\n\nexception"
            f" details:\n{safe_error}\n***"
            " end of debug info ***"
        ) from None

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
        items_raw: Any = []

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
