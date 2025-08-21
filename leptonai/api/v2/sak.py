from typing import Any

from ..v1.api_resource import APIResourse
from .types.sak import ListSAKResponseElement


class SAKAPI(APIResourse):
    def list_all(self) -> Any:
        """
        List all SAK tokens.

        Mimics v1 API style: returns raw JSON from GET /tokens.
        """
        response = self._get("/tokens")
        return self.ensure_list(response, ListSAKResponseElement)
