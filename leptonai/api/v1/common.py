from pydantic import BaseModel
from typing import TYPE_CHECKING, Dict, Union, List, Any, TypeVar

if TYPE_CHECKING:
    # only used for type hinting, but avoids circular imports
    from .workspace import Workspace


class APIResourse(object):
    _ws: "Workspace"

    def __init__(self, ws: "Workspace"):
        self._ws = ws
        self._get = ws._get
        self._post = ws._post
        self._put = ws._put
        self._patch = ws._patch
        self._delete = ws._delete
        self._head = ws._head

    T = TypeVar("T", bound=BaseModel)

    def safe_json(
        self, content: Union[T, List[T]]
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        if isinstance(content, BaseModel):
            return content.dict(exclude_none=True, by_alias=True)
        elif isinstance(content, list):
            return [item.dict(exclude_none=True, by_alias=True) for item in content]
        else:
            raise ValueError(
                "safe_json only accepts BaseModel or List[BaseModel] as input."
            )
