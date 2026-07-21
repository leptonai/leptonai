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
    def _to_name(self, name_or_deployment: Union[str, LeptonDeployment]) -> str:
        return (  # type: ignore
            name_or_deployment
            if isinstance(name_or_deployment, str)
            else name_or_deployment.metadata.id_
        )

    def _http_endpoint_to_model(self, raw: dict) -> LeptonDeployment:
        return LeptonDeployment(**translation.http_endpoint_to_legacy(raw))

    def list_all(self) -> List[LeptonDeployment]:
        # GET /endpoints returns a bare array by default (no pagination params
        # sent); ensure_json yields that list. Each item is an HTTPEndpoint.
        response = self._get("/endpoints")
        items = self.ensure_json(response)
        return [self._http_endpoint_to_model(item) for item in items]

    def create(self, spec: LeptonDeployment) -> bool:
        """Create an endpoint from a legacy deployment spec.

        The legacy spec is translated into the HTTPEndpoint create body
        (single "default" component; endpoint-level fields lifted out).

        @implements LEP-5664 (endpoint create via new API)
        """
        payload = translation.legacy_to_http_endpoint(self.safe_json(spec))
        response = self._post("/endpoints", json=payload)
        return self.ensure_ok(response)

    def get(self, name_or_deployment: Union[str, LeptonDeployment]) -> LeptonDeployment:
        response = self._get(f"/endpoints/{self._to_name(name_or_deployment)}")
        self._raise_if_not_ok(response)
        return self._http_endpoint_to_model(response.json())

    def _get_raw(self, name: str) -> dict:
        response = self._get(f"/endpoints/{name}")
        self._raise_if_not_ok(response)
        return response.json()

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
        name = self._to_name(name_or_deployment)
        raw = self._get_raw(name)
        payload = translation.legacy_to_http_endpoint_patch(raw, self.safe_json(spec))
        dryrun_param = "?dryrun=true" if dryrun else ""
        response = self._patch(f"/endpoints/{name}{dryrun_param}", json=payload)
        self._raise_if_not_ok(response)
        return self._http_endpoint_to_model(response.json())

    def stop(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> LeptonDeployment:
        """Scale the endpoint down to zero replicas via PATCH.

        The new API replaces ``spec.components`` wholesale, so the current
        endpoint is fetched first and every component's ``min_replicas`` is set
        to 0 (the "terminate" case in the dashboard's builder).
        """
        name = self._to_name(name_or_deployment)
        raw = self._get_raw(name)
        payload = translation.build_endpoint_stop_patch(raw)
        response = self._patch(f"/endpoints/{name}", json=payload)
        self._raise_if_not_ok(response)
        return self._http_endpoint_to_model(response.json())

    def delete(self, name_or_deployment: Union[str, LeptonDeployment]) -> bool:
        response = self._delete(f"/endpoints/{self._to_name(name_or_deployment)}")
        return self.ensure_ok(response)

    def restart(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> LeptonDeployment:
        # PUT /endpoints/:eid/restart (endpoint/handler.go) — same verb as legacy.
        response = self._put(f"/endpoints/{self._to_name(name_or_deployment)}/restart")
        self._raise_if_not_ok(response)
        return self._http_endpoint_to_model(response.json())

    def get_readiness(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> ReadinessIssue:
        """Not available on the new endpoint API.

        The new endpoint surface has no standalone ``/readiness`` route;
        readiness is folded into per-replica status. ``lep endpoint status``
        degrades this sub-call to an empty result and prints a note.
        """
        raise NewEndpointAPIUnsupported(
            "per-deployment readiness is not yet supported by the new endpoint"
            " API; readiness detail is available per-replica"
        )

    def get_termination(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> DeploymentTerminations:
        """Not available on the new endpoint API (see :meth:`get_readiness`)."""
        raise NewEndpointAPIUnsupported(
            "per-deployment termination history is not yet supported by the new"
            " endpoint API; termination detail is available per-replica"
        )

    def get_replicas(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> List[Replica]:
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
        replica_id = replica if isinstance(replica, str) else replica.metadata.id_
        response = self._get(
            f"/endpoints/{self._to_name(name_or_deployment)}/replicas/{replica_id}/log",
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
        # GET /endpoints/:eid/events returns the same event array shape as the
        # legacy deployment events route (events/handler_events.go).
        response = self._get(f"/endpoints/{self._to_name(name_or_deployment)}/events")
        return self.ensure_list(response, LeptonEvent)
