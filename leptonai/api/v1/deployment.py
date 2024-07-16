import warnings
from typing import Union, List, Iterator, Optional

from .api_resource import APIResourse
from .types.deployment import LeptonDeployment, TokenVar, TokenValue
from .types.events import LeptonEvent
from .types.readiness import ReadinessIssue
from .types.termination import DeploymentTerminations
from .types.replica import Replica


def make_token_vars_from_config(
    is_public: Optional[bool], tokens: Optional[List[str]]
) -> Optional[List[TokenVar]]:
    # Note that None is different from [] here. None means that the tokens are not
    # changed, while [] means that the tokens are cleared (aka, public deployment)
    if is_public is None and tokens is None:
        return None
    elif is_public and tokens:
        raise ValueError(
            "For access control, you cannot specify both is_public and token at the"
            " same time. Please specify either is_public=True with no tokens passed"
            " in, or is_public=False and tokens as a list."
        )
    else:
        if is_public:
            return []
        else:
            final_tokens = [
                TokenVar(value_from=TokenValue(token_name_ref="WORKSPACE_TOKEN"))
            ]
            if tokens:
                final_tokens.extend([TokenVar(value=token) for token in tokens])
            return final_tokens


class DeploymentAPI(APIResourse):
    def _to_name(self, name_or_deployment: Union[str, LeptonDeployment]) -> str:
        return (  # type: ignore
            name_or_deployment
            if isinstance(name_or_deployment, str)
            else name_or_deployment.metadata.id_
        )

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
        warnings.warn(
            "create_pod is deprecated. Use the api under leptonai.api.v1.pod"
            " instead, which is more explicit and gives more strict param checking.",
            DeprecationWarning,
        )
        if spec.spec is None:
            raise ValueError("LeptonDeploymentUserSpec must not be None.")
        spec.spec.is_pod = True
        # todo: pod-specific fields check if needed.
        return self.create(spec)

    def get(self, name_or_deployment: Union[str, LeptonDeployment]) -> LeptonDeployment:
        response = self._get(f"/deployments/{self._to_name(name_or_deployment)}")
        return self.ensure_type(response, LeptonDeployment)

    def update(
        self, name_or_deployment: Union[str, LeptonDeployment], spec: LeptonDeployment
    ) -> LeptonDeployment:
        response = self._patch(
            f"/deployments/{self._to_name(name_or_deployment)}",
            json=self.safe_json(spec),
        )
        return self.ensure_type(response, LeptonDeployment)

    def delete(self, name_or_deployment: Union[str, LeptonDeployment]) -> bool:
        response = self._delete(f"/deployments/{self._to_name(name_or_deployment)}")
        return self.ensure_ok(response)

    def restart(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> LeptonDeployment:
        response = self._put(
            f"/deployments/{self._to_name(name_or_deployment)}/restart"
        )
        return self.ensure_type(response, LeptonDeployment)

    def get_readiness(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> ReadinessIssue:
        response = self._get(
            f"/deployments/{self._to_name(name_or_deployment)}/readiness"
        )
        return self.ensure_type(response, ReadinessIssue)

    def get_termination(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> DeploymentTerminations:
        response = self._get(
            f"/deployments/{self._to_name(name_or_deployment)}/termination"
        )
        return self.ensure_type(response, DeploymentTerminations)

    def get_replicas(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> List[Replica]:
        response = self._get(
            f"/deployments/{self._to_name(name_or_deployment)}/replicas"
        )
        return self.ensure_list(response, Replica)

    def get_log(
        self,
        name_or_deployment: Union[str, LeptonDeployment],
        replica: Union[str, Replica],
        timeout: Optional[int] = None,
    ) -> Iterator[str]:
        """
        Gets the log of the given deployment's specified replica. The log is streamed
        in chunks until timeout is reached. If timeout is not specified, the log will be
        streamed indefinitely, although you should not rely on this behavior as connections
        can be dropped when streamed for a long time.
        """
        replica_id = replica if isinstance(replica, str) else replica.metadata.id_
        response = self._get(
            f"/deployments/{self._to_name(name_or_deployment)}/replicas/{replica_id}/log",
            stream=True,
            timeout=timeout,
        )
        if not response.ok:
            raise RuntimeError(
                f"API call failed with status code {response.status_code}. Details:"
                f" {response.text}"
            )
        for chunk in response.iter_content(chunk_size=None):
            if chunk:
                yield chunk.decode("utf8")

    def get_events(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> List[LeptonEvent]:
        response = self._get(f"/deployments/{self._to_name(name_or_deployment)}/events")
        return self.ensure_list(response, LeptonEvent)

    # TODO: implement api for the various metrics, but for now we will simply ask users
    # to view the metrics from the web portal.
