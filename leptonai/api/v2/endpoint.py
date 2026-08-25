"""EndpointAPI — the new /endpoints-based implementation of the deployment API.

This is the flag-on counterpart of :class:`leptonai.api.v2.deployment.DeploymentAPI`.
It exposes the same method surface and returns the same
:class:`LeptonDeployment`-shaped objects, but talks to the new ``/endpoints``
routes (LEP-5664) and translates request/response bodies via
:mod:`leptonai.api.v2.translation`, so CLI commands and SDK callers are
unaffected by the mode switch.

Route coverage (verified against api-server refs/base/main):
- list/create/get/update/delete + ``/:eid/restart`` + ``/:eid/history``
  (endpoint/handler.go)
- ``/:eid/replicas``, ``/:eid/replicas/:rid/log`` (handler_replica.go)
- ``/:eid/events`` (events/handler_events.go)

Deliberately NOT available on the new endpoint surface (no route exists), so
these degrade explicitly rather than 404:
- standalone readiness / termination: folded into per-replica status server
  side; there is no ``/endpoints/:eid/readiness`` or ``/termination`` route.
"""

import sys
import warnings
from typing import Union, List, Iterator, Optional

from .api_resource import APIResourse
from .types.deployment import LeptonDeployment
from .types.events import LeptonEvent
from .types.readiness import ReadinessIssue
from .types.termination import DeploymentTerminations
from .types.replica import Replica
from . import translation


class NewEndpointAPIUnsupported(RuntimeError):
    """Raised when a legacy sub-operation has no equivalent on the new endpoint
    API and cannot be silently emulated. Carries a user-facing message.
    """


class EndpointAPI(APIResourse):
    @staticmethod
    def _is_pod_object(value: Union[str, LeptonDeployment]) -> bool:
        return (
            not isinstance(value, str)
            and value.spec is not None
            and value.spec.is_pod is True
        )

    def _to_name(self, name_or_deployment: Union[str, LeptonDeployment]) -> str:
        if self._is_pod_object(name_or_deployment):
            raise ValueError(
                "A pod-flavoured LeptonDeployment must be handled through the"
                " DevPod API."
            )
        return (  # type: ignore
            name_or_deployment
            if isinstance(name_or_deployment, str)
            else name_or_deployment.metadata.id_
        )

    def _http_endpoint_to_model(self, raw: dict) -> LeptonDeployment:
        try:
            if not isinstance(raw, dict):
                raise TypeError(
                    f"expected an endpoint object, got {type(raw).__name__}"
                )
            model = LeptonDeployment(**translation.http_endpoint_to_legacy(raw))
            if model.metadata is None or not (
                model.metadata.name or model.metadata.id_
            ):
                raise ValueError("endpoint response is missing metadata.name")
            return model
        except Exception:
            if self._contains_api_token_material(raw):
                raise RuntimeError(
                    "The endpoint response could not be decoded. Response details were"
                    " redacted because they may contain sensitive authentication data."
                ) from None
            raise

    def list_all(self) -> List[LeptonDeployment]:
        # GET /endpoints returns a bare array by default (no pagination params
        # sent). Match APIResourse.ensure_list's compatibility behavior: one
        # malformed server item must not make every valid endpoint disappear.
        response = self._get("/endpoints")
        items = self.ensure_json(response)
        valid_items = []
        errors = []
        for index, item in enumerate(items):
            try:
                valid_items.append(self._http_endpoint_to_model(item))
            except Exception as e:
                errors.append(self._format_list_item_error(index, e, item))
        if errors:
            sys.stderr.write(
                f"[lepton-error] Skipped {len(errors)} invalid endpoint(s) when"
                " parsing list response:"
                + "".join(errors)
                + "\n"
            )
        return valid_items

    def validate_create(self, spec: LeptonDeployment) -> None:
        """Validate a create locally without issuing a request.

        The CLI uses this before deleting an existing workload for ``--rerun``
        so a translation error cannot turn rerun into delete-only.
        """
        if spec.spec is not None and spec.spec.is_pod is True:
            self._client.pod.validate_create(spec)
            return
        translation.legacy_to_http_endpoint(self.safe_json(spec))

    def create(self, spec: LeptonDeployment) -> bool:
        """Create an endpoint and preserve the historical boolean result."""
        if spec.spec is not None and spec.spec.is_pod is True:
            return self._client.pod.create(spec)
        payload = translation.legacy_to_http_endpoint(self.safe_json(spec))
        response = self._post("/endpoints", json=payload)
        return self.ensure_ok(response)

    def create_with_response(
        self,
        spec: LeptonDeployment,
        *,
        tolerate_legacy_response: bool = False,
    ) -> Union[LeptonDeployment, bool]:
        """Create an endpoint and return its legacy-shaped resource response.

        The legacy spec is translated into the HTTPEndpoint create body
        (single "default" component; endpoint-level fields lifted out), then
        the HTTPEndpoint response is translated back to LeptonDeployment.
        ``tolerate_legacy_response`` accepts an empty legacy success body for
        feature-disabled compatibility.

        @implements LEP-5664 (endpoint create via new API), LEP-6218 (return the
        successful translated endpoint create response)
        """
        if spec.spec is not None and spec.spec.is_pod is True:
            return self._client.pod.create(spec)
        payload = translation.legacy_to_http_endpoint(self.safe_json(spec))
        response = self._post("/endpoints", json=payload)
        if response.status_code >= 400:
            # The server may have generated a credential before a downstream
            # failure. Redact unconditionally; marker-based detection cannot
            # prove an arbitrary raw error body is token-free.
            response = self._redacted_response(response)
        self._raise_if_not_ok(response)
        try:
            return self._http_endpoint_to_model(response.json())
        except Exception:
            if tolerate_legacy_response and response.content.strip() in (b"", b"{}"):
                return True
            raise RuntimeError(
                "The create request succeeded, but the endpoint response could not be"
                " decoded."
            ) from None

    def create_pod(self, spec: LeptonDeployment) -> bool:
        """Deprecated DeploymentAPI-compatible DevPod creation shim."""
        warnings.warn(
            "create_pod is deprecated. Use the api under leptonai.api.v2.pod"
            " instead, which is more explicit and gives more strict param checking.",
            DeprecationWarning,
        )
        if spec.spec is None:
            raise ValueError("LeptonDeploymentUserSpec must not be None.")
        spec.spec.is_pod = True
        return self._client.pod.create(spec)

    def get(self, name_or_deployment: Union[str, LeptonDeployment]) -> LeptonDeployment:
        if self._is_pod_object(name_or_deployment):
            return self._client.pod.get(name_or_deployment)
        response = self._get(f"/endpoints/{self._to_name(name_or_deployment)}")
        return self._http_endpoint_to_model(self.ensure_json(response))

    def _get_raw(self, name: str) -> dict:
        response = self._get(f"/endpoints/{name}")
        return self.ensure_json(response)

    def update(
        self,
        name_or_deployment: Union[str, LeptonDeployment],
        spec: LeptonDeployment,
        dryrun: bool = False,
    ) -> LeptonDeployment:
        """Update an endpoint from a legacy deployment spec.

        The new API replaces ``spec.components`` wholesale, so the current
        endpoint is fetched first and the patch resends the full component array
        with the form's fields overlaid onto the frontend component (RFC7386
        merge). See :func:`translation.legacy_to_http_endpoint_patch`.

        @implements LEP-5664 (endpoint update via new API)
        """
        if self._is_pod_object(name_or_deployment) or (
            spec.spec is not None and spec.spec.is_pod is True
        ):
            return self._client.pod.update(name_or_deployment, spec)
        name = self._to_name(name_or_deployment)
        raw = self._get_raw(name)
        payload = translation.legacy_to_http_endpoint_patch(raw, self.safe_json(spec))
        dryrun_param = "?dryrun=true" if dryrun else ""
        response = self._patch(f"/endpoints/{name}{dryrun_param}", json=payload)
        return self._http_endpoint_to_model(self.ensure_json(response))

    def stop(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> LeptonDeployment:
        """Scale the endpoint down to zero replicas via PATCH.

        The new API replaces ``spec.components`` wholesale, so the current
        endpoint is fetched first and every component's ``min_replicas`` is set
        to 0 (the "terminate" case in the dashboard's builder).
        """
        if self._is_pod_object(name_or_deployment):
            return self._client.pod.stop(name_or_deployment)
        name = self._to_name(name_or_deployment)
        raw = self._get_raw(name)
        payload = translation.build_endpoint_stop_patch(raw)
        response = self._patch(f"/endpoints/{name}", json=payload)
        return self._http_endpoint_to_model(self.ensure_json(response))

    def delete(self, name_or_deployment: Union[str, LeptonDeployment]) -> bool:
        if self._is_pod_object(name_or_deployment):
            return self._client.pod.delete(name_or_deployment)
        response = self._delete(f"/endpoints/{self._to_name(name_or_deployment)}")
        return self.ensure_ok(response)

    def restart(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> LeptonDeployment:
        if self._is_pod_object(name_or_deployment):
            return self._client.pod.restart(name_or_deployment)
        # PUT /endpoints/:eid/restart (endpoint/handler.go) — same verb as legacy.
        response = self._put(f"/endpoints/{self._to_name(name_or_deployment)}/restart")
        return self._http_endpoint_to_model(self.ensure_json(response))

    def get_readiness(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> ReadinessIssue:
        """Not available on the new endpoint API.

        The new endpoint surface has no standalone ``/readiness`` route;
        readiness is folded into per-replica status. ``lep endpoint status``
        degrades this sub-call to an empty result and prints a note.
        """
        if self._is_pod_object(name_or_deployment):
            return self._client.pod.get_readiness(name_or_deployment)
        raise NewEndpointAPIUnsupported(
            "per-deployment readiness is not yet supported by the new endpoint"
            " API; readiness detail is available per-replica"
        )

    def get_termination(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> DeploymentTerminations:
        """Not available on the new endpoint API (see :meth:`get_readiness`)."""
        if self._is_pod_object(name_or_deployment):
            return self._client.pod.get_termination(name_or_deployment)
        raise NewEndpointAPIUnsupported(
            "per-deployment termination history is not yet supported by the new"
            " endpoint API; termination detail is available per-replica"
        )

    def get_replicas(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> List[Replica]:
        if self._is_pod_object(name_or_deployment):
            raise NewEndpointAPIUnsupported(
                "replica listing is not exposed by the new DevPod API"
            )
        # GET /endpoints/:eid/replicas returns the same Replica shape as the
        # legacy deployment replicas route (handler_replica.go).
        response = self._get(f"/endpoints/{self._to_name(name_or_deployment)}/replicas")
        return self.ensure_list(response, Replica)

    def get_log(
        self,
        name_or_deployment: Union[str, LeptonDeployment],
        replica: Union[str, Replica],
        timeout: Optional[int] = None,
    ) -> Iterator[str]:
        if self._is_pod_object(name_or_deployment):
            yield from self._client.pod.get_log(name_or_deployment, timeout=timeout)
            return
        replica_id = replica if isinstance(replica, str) else replica.metadata.id_
        response = self._get(
            f"/endpoints/{self._to_name(name_or_deployment)}/replicas/{replica_id}/log",
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
        if self._is_pod_object(name_or_deployment):
            raise NewEndpointAPIUnsupported(
                "events are not exposed by the new DevPod API"
            )
        # GET /endpoints/:eid/events returns the same event array shape as the
        # legacy deployment events route (events/handler_events.go).
        response = self._get(f"/endpoints/{self._to_name(name_or_deployment)}/events")
        return self.ensure_list(response, LeptonEvent)
