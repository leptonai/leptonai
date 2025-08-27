from typing import List

from .api_resource import APIResourse

from .types.secret import SecretItem


class SecretAPI(APIResourse):
    def list_all(self) -> List[SecretItem]:
        response = self._get("/secrets")
        try:
            data = self.ensure_json(response)
            if isinstance(data, list) and all(isinstance(x, str) for x in data):
                return [SecretItem(name=x) for x in data]
        except Exception:
            pass
        # Preferred path: typed list
        return self.ensure_list(response, SecretItem)

    def create(self, secrets: List[SecretItem]) -> bool:
        response = self._post("/secrets", json=self.safe_json(secrets))
        return self.ensure_ok(response)

    def delete(self, name: str) -> bool:
        response = self._delete(f"/secrets/{name}")
        return self.ensure_ok(response)
