"""DevPodAPI — the new /devpods-based implementation of the pod API.

This is the flag-on counterpart of :class:`leptonai.api.v2.pod.PodAPI`. It
exposes the same method surface and returns the same
:class:`LeptonDeployment`-shaped (pod) objects, but talks to the new
``/devpods`` routes (LEP-5665) and translates request/response bodies via
:mod:`leptonai.api.v2.translation`.

Route coverage (verified against api-server refs/base/main devpod/handler.go):
- list/create/get/update/delete + ``/:did/restart`` + ``/:did/history``
- ``/:did/shell``, ``/:did/network-connectivity``
- ``/:did/replicas`` (api-server/httpapi/handler_replica.go) — read only to
  confirm the single Ready pod a Teleport target belongs to; Teleport also
  checks ``dev_pod_teleport`` in ``/info/features``
- ``/:did/log`` (api-server/httpapi/log/handler_log.go) — historical Loki JSON
  is available by DevPod ID, but the legacy live-text stream requires a replica
  ID that the DevPod API does not expose.

Deliberately NOT available (no route exists on the devpod surface):
- ``/devpods/:did/events`` — verified missing; ``get_events`` is unsupported.

Stop/start uses the ``spec.stopped`` boolean switch (PATCH), not scale-to-zero.
"""

from dataclasses import dataclass
import json
import re
import sys
from typing import Any, Union, List, Iterator, Optional
from urllib.parse import quote
import warnings

from .api_resource import APIResourse
from .types.deployment import (
    LeptonDeployment,
    LeptonDeploymentState,
    LeptonDeploymentUserSpec,
)
from .types.readiness import ReadinessIssue
from .types.termination import DeploymentTerminations
from .types.teleport import TeleportConnection
from .pod import TeleportUnavailable
from . import translation


class NewDevPodAPIUnsupported(RuntimeError):
    """Raised when a legacy sub-operation has no equivalent on the new devpod
    API and cannot be silently emulated. Carries a user-facing message.
    """


_DNS_LABEL = re.compile(r"[a-z0-9](?:[-a-z0-9]*[a-z0-9])?")
_POD_UID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


@dataclass(frozen=True)
class DevPodTeleportNode:
    """The Teleport node a new-API Dev Pod registers as.

    The DevPod API publishes neither the Teleport proxy nor the Linux account,
    so only the registered hostname is known here.
    """

    hostname: str
    # Detect a replaced pod while browser SSO owns the terminal.
    binding: str


class DevPodAPI(APIResourse):
    def get_teleport_connection(
        self, name_or_pod: Union[str, LeptonDeployment]
    ) -> TeleportConnection:
        raise NewDevPodAPIUnsupported(
            "The new DevPod API does not publish Teleport connection details; "
            "use get_teleport_node() with the workspace's Teleport proxy."
        )

    def get_teleport_node(
        self, name_or_pod: Union[str, LeptonDeployment]
    ) -> DevPodTeleportNode:
        """Resolve the Teleport node of a Ready Dev Pod.

        Mirrors the dashboard's Teleport guide: the workspace must enable
        ``dev_pod_teleport`` and the Dev Pod must run exactly one Ready
        replica. The agent registers as ``<workspace>-<Dev Pod name>``.
        """
        name = self._to_name(name_or_pod)
        hostname = f"{self._client.workspace_id}-{name}"
        if not (
            isinstance(name, str)
            and _DNS_LABEL.fullmatch(name)
            and len(hostname) <= 253
            and all(_DNS_LABEL.fullmatch(label) for label in hostname.split("."))
        ):
            raise TeleportUnavailable("The Dev Pod's Teleport node name is invalid.")
        features = self.ensure_json(self._get("/info/features"))
        if not isinstance(features, dict):
            raise TeleportUnavailable("The workspace feature response is invalid.")
        # The flag is omitted when false.
        if features.get("dev_pod_teleport") is not True:
            raise TeleportUnavailable(
                "Teleport SSH is not enabled for Dev Pods in this workspace."
            )
        path = f"/devpods/{quote(name, safe='')}"
        pod = self.ensure_json(self._get(path))
        metadata = pod.get("metadata") if isinstance(pod, dict) else None
        spec = pod.get("spec") if isinstance(pod, dict) else None
        status = pod.get("status") if isinstance(pod, dict) else None
        if (
            not isinstance(metadata, dict)
            or metadata.get("name") != name
            or not isinstance(spec, dict)
            or not isinstance(status, dict)
        ):
            raise TeleportUnavailable("The API did not confirm the Dev Pod's identity.")
        if metadata.get("deleted_at") not in (None, 0):
            raise TeleportUnavailable(f"Dev Pod {name} is being deleted.")
        if spec.get("stopped") is True or status.get("state") != "Ready":
            state = "Stopped" if spec.get("stopped") is True else status.get("state")
            raise TeleportUnavailable(
                f"Dev Pod {name} is not Ready (state: {state or 'unknown'});"
                " Teleport SSH needs a running Dev Pod."
            )
        replicas = self.ensure_json(self._get(f"{path}/replicas"))
        if not isinstance(replicas, list) or len(replicas) != 1:
            raise TeleportUnavailable(
                "Teleport SSH requires exactly one Dev Pod replica. "
                "Wait for the pod to finish starting or restarting and retry."
            )
        replica = replicas[0] if isinstance(replicas[0], dict) else {}
        replica_meta = replica.get("metadata")
        rid = replica_meta.get("id") if isinstance(replica_meta, dict) else None
        rid = rid if rid is not None else replica.get("id")
        replica_status = replica.get("status")
        if not isinstance(replica_status, dict):
            replica_status = {}
        readiness = replica_status.get("readiness_issue")
        pod_uid = replica_status.get("pod_uid")
        if not isinstance(rid, str) or not rid.strip():
            raise TeleportUnavailable("The Dev Pod replica is missing its ID.")
        if not isinstance(readiness, dict) or readiness.get("reason") != "Ready":
            raise TeleportUnavailable(
                "The Dev Pod replica is not Ready. Retry when the pod is running."
            )
        if not isinstance(pod_uid, str) or not _POD_UID.fullmatch(pod_uid):
            raise TeleportUnavailable(
                "The Dev Pod did not report its current replica identity."
            )
        return DevPodTeleportNode(
            hostname=hostname,
            binding=json.dumps({"replica": rid, "pod_uid": pod_uid}, sort_keys=True),
        )

    def _to_name(self, name_or_pod: Union[str, LeptonDeployment]) -> str:
        return (  # type: ignore
            name_or_pod if isinstance(name_or_pod, str) else name_or_pod.metadata.id_
        )

    def get_shell_replica(
        self, name_or_pod: Union[str, LeptonDeployment], replica: Optional[str] = None
    ) -> Optional[str]:
        """Confirm the DevPod can run a shell; the route picks its container."""
        if replica is not None:
            raise NewDevPodAPIUnsupported(
                "--replica is not supported by the new DevPod API: its shell always"
                " opens in the Dev Pod's current container."
            )
        pod = self.get(name_or_pod)
        requirement = pod.spec.resource_requirement if pod.spec else None
        state = (pod.status.phase or pod.status.state) if pod.status else None
        if (requirement is not None and requirement.min_replicas == 0) or (
            state != LeptonDeploymentState.Ready
        ):
            shown = getattr(state, "value", state) or "unknown"
            raise NewDevPodAPIUnsupported(
                f"Pod {self._to_name(name_or_pod)} is not Ready (state: {shown});"
                " a shell needs a running Dev Pod."
            )
        return None

    def shell_connection(
        self,
        name_or_pod: Union[str, LeptonDeployment],
        replica_id: Optional[str] = None,
    ) -> Any:
        """Open the DevPod shell WebSocket; the server resolves the active pod."""
        name = quote(self._to_name(name_or_pod), safe="")
        return self._open_shell(f"/devpods/{name}/shell")

    def _http_devpod_to_model(self, raw: dict) -> LeptonDeployment:
        if not isinstance(raw, dict):
            raise TypeError(f"expected a DevPod object, got {type(raw).__name__}")
        model = LeptonDeployment(**translation.http_devpod_to_legacy(raw))
        if model.metadata is None or not (model.metadata.name or model.metadata.id_):
            raise ValueError("DevPod response is missing metadata.name")
        return model

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
        if spec.allow_unauthenticated_access is not None:
            raise ValueError(
                "allow_unauthenticated_access applies only to endpoints and cannot"
                " be set on a pod spec."
            )
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
        # GET /devpods returns a bare array of HTTPDevPod by default. Preserve
        # ensure_list's per-item tolerance for compatibility with legacy lists.
        response = self._get("/devpods")
        items = self.ensure_json(response)
        valid_items = []
        errors = []
        for index, item in enumerate(items):
            try:
                valid_items.append(self._http_devpod_to_model(item))
            except Exception as e:
                errors.append(f"\n index {index}: {e}\nitem: {item}")
        if errors:
            sys.stderr.write(
                f"[lepton-error] Skipped {len(errors)} invalid devpod(s) when parsing"
                " list response:"
                + "".join(errors)
                + "\n"
            )
        return valid_items

    def validate_create(self, spec: LeptonDeployment) -> None:
        """Validate a create locally without mutating the supplied model."""
        if spec.spec is not None and spec.spec.is_pod is not True:
            raise ValueError("The spec is not a pod spec.")
        if spec.spec is not None and spec.spec.allow_unauthenticated_access is not None:
            raise ValueError(
                "allow_unauthenticated_access applies only to endpoints and cannot"
                " be set on a pod spec."
            )
        translation.legacy_to_http_devpod(self.safe_json(spec))

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
    ) -> Iterator[str]:
        """Reject the unavailable legacy live-text stream explicitly.

        ``GET /devpods/:did/log`` without ``replica=`` returns a bounded Loki
        JSON response. The backend selects its live kubelet stream only when a
        replica ID is supplied, but no DevPod replica-list/status contract
        exposes that ID. Yielding the JSON transport as if it were live log text
        would silently violate :meth:`PodAPI.get_log` semantics.
        """
        raise NewDevPodAPIUnsupported(
            "live DevPod log streaming is not yet supported by the new DevPod API; "
            "the dedicated route only exposes bounded historical logs"
        )
