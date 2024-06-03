from typing import Union

from .common import APIResourse
from .types.deployment import LeptonDeployment


class DeploymentAPI(APIResourse):
    def list_all(self):
        response = self._get("/deployments")
        return self.ensure_list(response, LeptonDeployment)

    def create(self, spec: LeptonDeployment):
        """
        Create a deployment with the given deployment spec.
        """
        response = self._post("/deployments", json=self.safe_json(spec))
        return self.ensure_ok(response)

    def create_pod(self, spec: LeptonDeployment):
        """
        Creates a pod with the given deployment spec. This is equivalent to creating a deployment
        with is_pod=True.
        """
        if spec.spec is None:
            raise ValueError("LeptonDeploymentUserSpec must not be None.")
        spec.spec.is_pod = True
        # todo: pod-specific fields check if needed.
        return self.create(spec)

    def get(self, name_or_deployment: Union[str, LeptonDeployment]) -> LeptonDeployment:
        name = (
            name_or_deployment
            if isinstance(name_or_deployment, str)
            else name_or_deployment.metadata.name
        )
        response = self._get(f"/deployments/{name}")
        return self.ensure_type(response, LeptonDeployment)

    def update(
        self, name_or_deployment: Union[str, LeptonDeployment], spec: LeptonDeployment
    ) -> LeptonDeployment:
        name = (
            name_or_deployment
            if isinstance(name_or_deployment, str)
            else name_or_deployment.metadata.name
        )
        response = self._patch(f"/deployments/{name}", json=self.safe_json(spec))
        return self.ensure_type(response, LeptonDeployment)

    def delete(self, name_or_deployment: Union[str, LeptonDeployment]) -> bool:
        name = (
            name_or_deployment
            if isinstance(name_or_deployment, str)
            else name_or_deployment.metadata.name
        )
        response = self._delete(f"/deployments/{name}")
        return self.ensure_ok(response)

    def restart(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> LeptonDeployment:
        name = (
            name_or_deployment
            if isinstance(name_or_deployment, str)
            else name_or_deployment.metadata.name
        )
        response = self._put(f"/deployments/{name}/restart")
        return self.ensure_type(response, LeptonDeployment)
