from typing import List, Union, Optional

from loguru import logger


from .common import APIResourse
from .types.deployment import LeptonDeployment


class DeploymentAPI(APIResourse):
    def list_all(self):
        response = self._get("/deployments")
        return self._ws.ensure_list(response, LeptonDeployment)

    def create(self, spec: LeptonDeployment):
        """
        Run a photon with the given deployment spec.
        """
        response = self._post("/deployments", json=spec.dict(exclude_none=True))
        return self._ws.ensure_ok(response)

    def get(self, name_or_deployment: Union[str, LeptonDeployment]) -> LeptonDeployment:
        name = (
            name_or_deployment
            if isinstance(name_or_deployment, str)
            else name_or_deployment.metadata.name
        )
        response = self._get(f"/deployments/{name}")
        return self._ws.ensure_type(response, LeptonDeployment)

    def update(
        self, name_or_deployment: Union[str, LeptonDeployment], spec: LeptonDeployment
    ) -> LeptonDeployment:
        name = (
            name_or_deployment
            if isinstance(name_or_deployment, str)
            else name_or_deployment.metadata.name
        )
        response = self._patch(
            f"/deployments/{name}", json=spec.dict(exclude_none=True)
        )
        return self._ws.ensure_type(response, LeptonDeployment)

    def delete(self, name_or_deployment: Union[str, LeptonDeployment]) -> bool:
        name = (
            name_or_deployment
            if isinstance(name_or_deployment, str)
            else name_or_deployment.metadata.name
        )
        response = self._delete(f"/deployments/{name}")
        return self._ws.ensure_ok(response)

    def restart(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> LeptonDeployment:
        name = (
            name_or_deployment
            if isinstance(name_or_deployment, str)
            else name_or_deployment.metadata.name
        )
        response = self._put(f"/deployments/{name}/restart")
        return self._ws.ensure_type(response, LeptonDeployment)
