from typing import Union, List

from .common import APIResourse

from .types.common import SecretItem


class SecretAPI(APIResourse):
    def list_all(self):
        response = self._get("/secrets")
        return self._ws.ensure_json(response)

    def create(self, secrets: Union[SecretItem, List[SecretItem]]) -> bool:
        if isinstance(secrets, SecretItem):
            serialized = [secrets.dict()]
        else:
            serialized = [s.dict() for s in secrets]
        response = self._post("/secrets", json=serialized)
        return self._ws.ensure_ok(response)

    def delete(self, name: str) -> bool:
        response = self._delete(f"/secrets/{name}")
        return self._ws.ensure_ok(response)
