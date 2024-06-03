from typing import Union, List

from .common import APIResourse

from .types.common import SecretItem


class SecretAPI(APIResourse):
    def list_all(self):
        response = self._get("/secrets")
        return self.ensure_json(response)

    def create(self, secrets: Union[SecretItem, List[SecretItem]]) -> bool:
        response = self._post("/secrets", json=self.safe_json(secrets))
        return self.ensure_ok(response)

    def delete(self, name: str) -> bool:
        response = self._delete(f"/secrets/{name}")
        return self.ensure_ok(response)
