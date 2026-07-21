"""DevPodAPI — the new /devpods-based implementation of the pod API.

This is the flag-on counterpart of :class:`leptonai.api.v2.pod.PodAPI`. It
exposes the same method surface and returns the same
:class:`LeptonDeployment`-shaped (pod) objects, but talks to the new
``/devpods`` routes (LEP-5665) and translates request/response bodies via
:mod:`leptonai.api.v2.translation`.

Route coverage (verified against api-server refs/base/main devpod/handler.go):
- list/create/get/update/delete + ``/:did/restart`` + ``/:did/history``
- ``/:did/shell``, ``/:did/network-connectivity``

Deliberately NOT available (no route exists on the devpod surface):
- ``/devpods/:did/events`` — verified missing; ``get_events`` is unsupported.
- per-replica log path — devpods run a single pod; the legacy PodAPI derived
  logs from the single replica. The new devpod API has no replica log route, so
  ``get_log`` degrades explicitly.

Stop/start uses the ``spec.stopped`` boolean switch (PATCH), not scale-to-zero.
"""

from typing import Union, List, Optional
import warnings

from .api_resource import APIResourse
from .types.deployment import LeptonDeployment, LeptonDeploymentUserSpec
from .types.readiness import ReadinessIssue
from .types.termination import DeploymentTerminations
from . import translation


class NewDevPodAPIUnsupported(RuntimeError):
    """Raised when a legacy sub-operation has no equivalent on the new devpod
    API and cannot be silently emulated. Carries a user-facing message.
    """


class DevPodAPI(APIResourse):
    def _to_name(self, name_or_pod: Union[str, LeptonDeployment]) -> str:
        return (  # type: ignore
            name_or_pod if isinstance(name_or_pod, str) else name_or_pod.metadata.id_
        )

    def _http_devpod_to_model(self, raw: dict) -> LeptonDeployment:
        return LeptonDeployment(**translation.http_devpod_to_legacy(raw))

    def _sanity_check_pod_spec(self, spec: Optional[LeptonDeploymentUserSpec]):
        """Mirror the legacy PodAPI sanity checks so behavior is identical
        regardless of mode. Fields with no effect in a pod are warned + cleared;
        the translation layer additionally drops them from the devpod payload.
        """
        if spec is None:
            warnings.warn(
                "You have not specified a pod spec - is that intentional?",
                RuntimeWarning,
            )
            return None
        if not spec.is_pod:
            raise ValueError("The spec is not a pod spec.")
        if spec.resource_requirement:
            if spec.resource_requirement.min_replicas not in (None, 1):
                warnings.warn(
                    "min_replicas does not take effect in pod spec.", RuntimeWarning
                )
                spec.resource_requirement.min_replicas = 1
            if spec.resource_requirement.max_replicas not in (None, 1):
                warnings.warn(
                    "max_replicas does not take effect in pod spec.", RuntimeWarning
                )
                spec.resource_requirement.max_replicas = 1
        if spec.auto_scaler:
            warnings.warn(
                "Auto scaler does not take effect in pod spec.", RuntimeWarning
            )
            spec.auto_scaler = None
        if spec.api_tokens:
            warnings.warn("API tokens do not take effect in pod spec.", RuntimeWarning)
            spec.api_tokens = None
        return spec

    def list_all(self) -> List[LeptonDeployment]:
        # GET /devpods returns a bare array of HTTPDevPod by default.
        response = self._get("/devpods")
        items = self.ensure_json(response)
        return [self._http_devpod_to_model(item) for item in items]

    def create(self, spec: LeptonDeployment) -> bool:
        """Create a devpod from a legacy pod deployment spec.

        @implements LEP-5665 (devpod create via new API)
        """
        spec.spec = self._sanity_check_pod_spec(spec.spec)
        payload = translation.legacy_to_http_devpod(self.safe_json(spec))
        response = self._post("/devpods", json=payload)
        return self.ensure_ok(response)

    def get(self, name_or_pod: Union[str, LeptonDeployment]) -> LeptonDeployment:
        response = self._get(f"/devpods/{self._to_name(name_or_pod)}")
        self._raise_if_not_ok(response)
        return self._http_devpod_to_model(response.json())

    def update(
        self, name_or_deployment: Union[str, LeptonDeployment], spec: LeptonDeployment
    ) -> LeptonDeployment:
        # Matches legacy PodAPI: updating a pod is not supported.
        raise RuntimeError(
            "Updating a pod is not supported. Updating a pod will cause all pod"
            " resources (including local storage) to be lost, and we strongly recommend"
            " you to be careful in doing so."
        )

    def stop(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> LeptonDeployment:
        """Stop the devpod via the ``spec.stopped`` switch (PATCH).

        The new devpod API uses ``{"spec": {"stopped": true}}`` rather than
        scaling to zero replicas (devpod-api.ts ``podStopPatch``).
        """
        name = self._to_name(name_or_deployment)
        response = self._patch(f"/devpods/{name}", json={"spec": {"stopped": True}})
        self._raise_if_not_ok(response)
        return self._http_devpod_to_model(response.json())

    def delete(self, name_or_deployment: Union[str, LeptonDeployment]) -> bool:
        response = self._delete(f"/devpods/{self._to_name(name_or_deployment)}")
        return self.ensure_ok(response)

    def restart(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> LeptonDeployment:
        # PUT /devpods/:did/restart (devpod/handler.go).
        response = self._put(f"/devpods/{self._to_name(name_or_deployment)}/restart")
        self._raise_if_not_ok(response)
        return self._http_devpod_to_model(response.json())

    def get_readiness(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> ReadinessIssue:
        """Not available on the new devpod API — no standalone readiness route."""
        raise NewDevPodAPIUnsupported(
            "readiness detail is not yet supported by the new devpod API"
        )

    def get_termination(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> DeploymentTerminations:
        """Not available on the new devpod API — no standalone termination route."""
        raise NewDevPodAPIUnsupported(
            "termination detail is not yet supported by the new devpod API"
        )

    def get_log(
        self,
        name_or_deployment: Union[str, LeptonDeployment],
        timeout: Optional[int] = None,
    ):
        """Not available on the new devpod API.

        The new devpod surface has no per-replica log route. ``lep pod log``
        degrades to a clear message rather than 404.
        """
        raise NewDevPodAPIUnsupported(
            "streaming logs is not yet supported by the new devpod API; use the"
            " web portal to view devpod logs"
        )
