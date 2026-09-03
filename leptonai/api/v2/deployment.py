import warnings
from typing import Union, List, Iterator, Optional

from .api_resource import APIResourse
from .types.deployment import LeptonDeployment, TokenVar
from .types.events import LeptonEvent
from .types.readiness import ReadinessIssue
from .types.termination import DeploymentTerminations
from .types.replica import Replica


def normalize_endpoint_authentication_payload(
    payload: dict,
    *,
    for_update: bool = False,
) -> dict:
    """Validate and atomically encode endpoint authentication fields.

    ``allow_unauthenticated_access=true`` is an explicit mode transition. The
    server accepts an omitted token list on create, but including ``[]`` keeps
    create and PATCH semantics unambiguous and prevents a PATCH merge from
    retaining live credentials. A redaction sentinel is never a usable token.
    """
    spec = payload.get("spec")
    if not isinstance(spec, dict):
        return payload
    if spec.get("is_pod") is True:
        if "allow_unauthenticated_access" in spec:
            raise ValueError(
                "allow_unauthenticated_access applies only to endpoints and cannot"
                " be set on a pod spec."
            )
        return payload

    tokens = spec.get("api_tokens")
    has_token_field = "api_tokens" in spec
    has_allow_field = "allow_unauthenticated_access" in spec
    allow_unauthenticated = spec.get("allow_unauthenticated_access")
    if allow_unauthenticated is True:
        if tokens:
            raise ValueError(
                "allow_unauthenticated_access=true cannot be combined with API tokens."
            )
        spec["api_tokens"] = []
    elif (
        for_update and has_allow_field and allow_unauthenticated is False and not tokens
    ):
        raise ValueError(
            "allow_unauthenticated_access=false requires at least one API token."
        )
    elif for_update and has_token_field and not tokens:
        raise ValueError(
            "Clearing API tokens requires allow_unauthenticated_access=true in the"
            " same update."
        )

    for token in spec.get("api_tokens") or []:
        if isinstance(token, dict) and token.get("value") == "***":
            raise ValueError(
                "'***' is a redacted API-token placeholder, not a usable token."
                " Supply a real token instead."
            )
    return payload


def endpoint_payload_may_generate_api_token(payload: dict) -> bool:
    """Whether an endpoint create leaves token generation to the server."""
    spec = payload.get("spec")
    return (
        isinstance(spec, dict)
        and spec.get("is_pod") is not True
        and not spec.get("allow_unauthenticated_access")
        and not spec.get("api_tokens")
    )


def warn_if_create_may_hide_generated_token(payload: dict) -> None:
    """Warn when the compatibility boolean API may discard a generated token.

    Do not predicate this warning on a cached workspace-feature snapshot. A
    server rollout can enable secure defaults after that snapshot was taken,
    while the create request is still in flight.
    """
    if endpoint_payload_may_generate_api_token(payload):
        warnings.warn(
            "create() returns only a boolean and cannot expose a token that a"
            " secure-default server may generate. Use create_with_response() when"
            " the create request does not supply an authentication mode.",
            RuntimeWarning,
            stacklevel=3,
        )


def make_token_vars_from_config(
    is_public: Optional[bool], tokens: Optional[List[str]]
) -> Optional[List[TokenVar]]:
    # Note that None is different from [] here. None means that the tokens are not
    # changed, while [] means that the tokens are cleared (aka, no tokens)

    if tokens is None and is_public is None:
        return None

    if is_public and not tokens:
        return []

    # Workspace token is no longer accessible
    final_tokens = []
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

    def validate_create(self, spec: LeptonDeployment) -> None:
        """Validate authentication fields without issuing a create request."""
        normalize_endpoint_authentication_payload(self.safe_json(spec))

    def create(self, spec: LeptonDeployment) -> bool:
        """Create a deployment and preserve the historical boolean result.

        When authentication is unspecified, a secure-default server may return a
        generated credential that this compatibility method does not expose. Use
        :meth:`create_with_response` to receive the created resource and token.
        """
        payload = normalize_endpoint_authentication_payload(self.safe_json(spec))
        warn_if_create_may_hide_generated_token(payload)
        response = self._post("/deployments", json=payload)
        status_code = getattr(response, "status_code", 0)
        if isinstance(status_code, int) and status_code >= 400:
            if status_code >= 500 and endpoint_payload_may_generate_api_token(payload):
                response = self._redacted_response(response)
            else:
                response = self._response_for_diagnostic(
                    response,
                    sensitive_values=self._api_token_literal_values(payload),
                )
        return self.ensure_ok(response)

    def create_with_response(
        self,
        spec: LeptonDeployment,
        *,
        tolerate_legacy_response: bool = False,
    ) -> Union[LeptonDeployment, bool]:
        """Create a deployment and return the successful resource response.

        Non-pod creates return the deployment emitted by the API, including any
        generated API token. Pod creates delegate to :meth:`create` and retain
        their legacy boolean result. ``tolerate_legacy_response`` lets the CLI
        preserve feature-disabled behavior with older servers whose successful
        create response was empty (including an empty JSON object).

        @implements LEP-6218 (return the successful deployment create response)
        """
        if spec.spec is not None and spec.spec.is_pod is True:
            return self.create(spec)

        payload = normalize_endpoint_authentication_payload(self.safe_json(spec))
        response = self._post("/deployments", json=payload)
        status_code = getattr(response, "status_code", 0)
        if isinstance(status_code, int) and status_code >= 400:
            if status_code >= 500 and endpoint_payload_may_generate_api_token(payload):
                # A generated credential can precede a downstream failure and
                # need not be labelled in an arbitrary error body.
                response = self._redacted_response(response)
            else:
                response = self._response_for_diagnostic(
                    response,
                    sensitive_values=self._api_token_literal_values(payload),
                )
        self._raise_if_not_ok(response)
        try:
            raw = response.json()
            if self._has_misplaced_api_token_field(raw):
                raise ValueError("deployment response has a misplaced token field")
            model = LeptonDeployment(**raw)
            if model.metadata is None or not (
                model.metadata.name or model.metadata.id_
            ):
                raise ValueError("deployment response is missing metadata.name")
            if model.spec is None:
                raise ValueError("deployment response is missing spec")
            return model
        except Exception:
            if tolerate_legacy_response and response.content.strip() in (b"", b"{}"):
                return True
            raise RuntimeError(
                "The create request succeeded, but the deployment response could not"
                " be decoded."
            ) from None

    def create_pod(self, spec: LeptonDeployment):
        """
        Creates a pod with the given deployment spec. This is equivalent to creating a deployment
        with is_pod=True.
        """
        warnings.warn(
            "create_pod is deprecated. Use the api under leptonai.api.v2.pod"
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
        self,
        name_or_deployment: Union[str, LeptonDeployment],
        spec: LeptonDeployment,
        dryrun: bool = False,
    ) -> LeptonDeployment:
        dryrun_param = "" if not dryrun else "?dryrun=true"

        payload = normalize_endpoint_authentication_payload(
            self.safe_json(spec),
            for_update=True,
        )
        response = self._patch(
            f"/deployments/{self._to_name(name_or_deployment)+dryrun_param}",
            json=payload,
        )
        status_code = getattr(response, "status_code", 0)
        if isinstance(status_code, int) and status_code >= 400:
            response = self._response_for_diagnostic(
                response,
                sensitive_values=self._api_token_literal_values(payload),
            )
        return self.ensure_type(response, LeptonDeployment)

    def stop(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> LeptonDeployment:
        """Scale the deployment down to zero replicas via PATCH.

        This issues a partial update equivalent to:
        {
          "spec": { "resource_requirement": { "min_replicas": 0 } }
        }
        """
        payload = {
            "spec": {
                "resource_requirement": {
                    "min_replicas": 0,
                }
            }
        }
        response = self._patch(
            f"/deployments/{self._to_name(name_or_deployment)}",
            json=payload,
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
                f" {self._response_text_for_diagnostic(response)}"
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
