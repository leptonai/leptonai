from typing import TYPE_CHECKING, Type

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
