# todo
from typing import Union
from .api_resource import APIResourse
from .types.deployment import LeptonDeployment
from .types.ingress import LeptonIngressEndpoint
from .types.ingress import LeptonIngress


class IngressAPI(APIResourse):
    def _to_name(self, name_or_ingress: Union[str, LeptonIngress]) -> str:
        return (
            name_or_ingress
            if isinstance(name_or_ingress, str)
            else name_or_ingress.metadata.id_
        )

    def list_all(self):
        response = self._get("/ingress")
        return self.ensure_list(response, LeptonIngress)

    def create(self, spec: LeptonIngress):
        """
        Create an ingress with the given Ingress spec.
        """
        response = self._post("/ingress", json=self.safe_json(spec))
        return self.ensure_ok(response)

    def get(self, name_or_ingress: Union[str, LeptonIngress]) -> LeptonIngress:
        response = self._get(f"/ingress/{self._to_name(name_or_ingress)}")
        return self.ensure_type(response, LeptonIngress)

    def delete(self, name_or_ingress: Union[str, LeptonIngress]) -> bool:
        response = self._delete(f"/ingress/{self._to_name(name_or_ingress)}")
        return self.ensure_ok(response)

    def update(
        self, name_or_ingress: Union[str, LeptonIngress], spec: LeptonIngress
    ) -> Union[LeptonIngress, str]:
        response = self._patch(
            f"/ingress/{self._to_name(name_or_ingress)}", json=self.safe_json(spec)
        )
        return self.ensure_type(response, LeptonIngress)

    def create_endpoint(
        self, name_or_ingress: Union[str, LeptonIngress], spec: LeptonIngressEndpoint
    ) -> LeptonIngress:
        """
        Create a ingressEndpoint with the given LeptonIngress IngressEndpoint spec.
        """
        response = self._post(
            f"/ingress/{self._to_name(name_or_ingress)}/endpoint/deployment",
            json=self.safe_json(spec),
        )
        return self.ensure_type(response, LeptonIngress)

    def delete_endpoint(
        self,
        name_or_ingress: Union[str, LeptonIngress],
        name_or_deployment: Union[str, LeptonDeployment, LeptonIngressEndpoint],
    ) -> LeptonIngress:
        """
        Deletes an endpoint for a given ingress and deployment.

        Args:
            name_or_ingress (Union[str, LeptonIngress]): The ingress name or an instance of LeptonIngress.
            dname_or_deployment_or_ingressendpoint (Union[str, LeptonDeployment, LeptonIngressEndpoint]):
                The deployment name,
                a string, or an instance of LeptonDeployment, or an instance of LeptonIngressEndpoint.

        Returns:
            LeptonIngress: The response from the deletion request, as a LeptonIngress object.

        This method converts the provided ingress and deployment to their respective names,
        constructs the appropriate URL, sends a DELETE request, and returns the response.
        """

        name = self._to_name(name_or_ingress)
        deployment_name = self._to_name(name_or_deployment)
        url = f"/ingress/{name}/endpoint/deployment/{deployment_name}"

        response = self.delete(url)
        return self.ensure_type(response, LeptonIngress)
