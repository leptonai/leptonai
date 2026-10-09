"""Workspace Teleport gates shared by the Pod, DevPod, and Job APIs."""

from typing import Any


class TeleportUnavailable(RuntimeError):
    """The workspace or workload cannot provide a usable Teleport target."""


def require_teleport_feature(api: Any, flag: str, workloads: str) -> None:
    """Fail unless ``/info/features`` enables Teleport for ``workloads``.

    Like the dashboard, a false or omitted flag means disabled; the API omits
    false booleans.
    """
    features = api.ensure_json(api._get("/info/features"))
    if not isinstance(features, dict):
        raise TeleportUnavailable("The workspace feature response is invalid.")
    if features.get(flag) is not True:
        raise TeleportUnavailable(
            f"Teleport SSH is not enabled for {workloads} in this workspace ({flag})."
        )
