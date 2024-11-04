from typing import Union, List, Iterator, Optional

from .api_resource import APIResourse
from .types.deployment import LeptonDeployment

from .types.job import LeptonJob


class TunaAPI(APIResourse):
    def train(self, spec: LeptonJob) -> LeptonJob:
        """
        Run a photon with the given job spec.
        """
        response = self._post("/fine-tune/models", json=self.safe_json(spec), is_tuna=True)
        return self.ensure_type(response, LeptonJob)

    def run(self, spec: LeptonDeployment):
        """
        Create a deployment with the given deployment spec.
        """
        response = self._post("/deployments", json=self.safe_json(spec), is_tuna=True)
        return self.ensure_ok(response)

    def get(self):
        """
        Create a deployment with the given deployment spec.
        """
        response = self._get("/fine-tune/models", is_tuna=True)
        return response

    def delete(self, model_id: str) -> bool:
        response = self._delete(f"/fine-tune/models/{model_id}")
        return self.ensure_ok(response)