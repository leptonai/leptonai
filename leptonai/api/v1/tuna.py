from .api_resource import APIResourse

from .types.job import LeptonJob
from .types.tuna import TunaModel


class TunaAPI(APIResourse):
    def train(self, model: TunaModel) -> LeptonJob:
        """
        Run a photon with the given job spec.
        """
        response = self._post(
            "/fine-tune/models", json=self.safe_json(model), is_tuna=True
        )
        return self.ensure_ok(response)

    def run(self, id, spec: TunaModel):
        """
        Create a deployment with the given deployment spec.
        """
        response = self._post(
            f"/fine-tune/models/{id}/deployments",
            json=self.safe_json(spec),
            is_tuna=True,
        )
        return self.ensure_ok(response)

    def get(self):
        """
        Create a deployment with the given deployment spec.
        """
        response = self._get("/fine-tune/models", is_tuna=True)
        return self.ensure_list(response, TunaModel)

    def delete(self, model_name: str) -> bool:
        response = self._delete(f"/fine-tune/models/{model_name}", is_tuna=True)
        return self.ensure_ok(response)
