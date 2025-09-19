from typing import List

from .api_resource import APIResourse

from .types.secret import SecretItem


class SecretAPI(APIResourse):
    def list_all(self) -> List[SecretItem]:
        response = self._get("/usersecrets")
        return self.ensure_list(response, SecretItem)

    def create(self, secrets: List[SecretItem]) -> bool:
        response = self._post("/usersecrets", json=self.safe_json(secrets))
        return self.ensure_ok(response)

    def delete(self, name: str) -> bool:
        response = self._delete(f"/usersecrets/{name}")
        return self.ensure_ok(response)
