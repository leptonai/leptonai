"""Decide whether, and in which replica, a workspace ``/shell`` session opens.

These rules mirror the dashboard terminal: it never offers a replica whose
container is gone, and hides the terminal of platform-managed tuning jobs.
Replica lists are read raw so callers see the readiness field the typed
``Replica`` model drops.
"""

import re
from typing import Any, FrozenSet, List, Optional


# Readiness reasons the dashboard treats as a stopped replica.
NON_EXECUTABLE_REPLICA_REASONS = frozenset(
    {"Completed", "Failed", "Deleted", "Terminated"}
)
# The dashboard's Ray replica table does not count "Terminated" as stopped.
RAY_STOPPED_REPLICA_REASONS = frozenset({"Completed", "Failed", "Deleted"})
# Images of the platform's tuning pipeline, whose terminal the dashboard hides.
_LEPTON_SYSTEM_IMAGE = re.compile(
    r"(?:docker\.io/)?leptonai/(?:l3m|lep-tuner)(?::[A-Za-z0-9_.-]+)?\Z"
    r"|[^/]+/lepton:tuna"
)
_LISTED_REPLICA_LIMIT = 10


class ShellUnavailable(RuntimeError):
    """No shell target could be selected; the message is user-facing."""


def is_lepton_system_image(image: Any) -> bool:
    return isinstance(image, str) and _LEPTON_SYSTEM_IMAGE.match(image) is not None


def _replica_id(item: Any) -> Optional[str]:
    if not isinstance(item, dict):
        return None
    metadata = item.get("metadata")
    rid = metadata.get("id") if isinstance(metadata, dict) else None
    if rid is None:
        rid = item.get("id")
    return rid if isinstance(rid, str) and rid.strip() else None


def _stopped(item: dict, reasons: FrozenSet[str]) -> bool:
    status = item.get("status")
    readiness = status.get("readiness_issue") if isinstance(status, dict) else None
    reason = readiness.get("reason") if isinstance(readiness, dict) else None
    return reason in reasons


def _created_at(item: dict) -> float:
    metadata = item.get("metadata")
    created = metadata.get("created_at") if isinstance(metadata, dict) else None
    return created if isinstance(created, (int, float)) else 0


def _sentence(text: str) -> str:
    return text[:1].upper() + text[1:]


def _listed(ids: List[str]) -> str:
    shown = ", ".join(ids[:_LISTED_REPLICA_LIMIT])
    return shown + (", ..." if len(ids) > _LISTED_REPLICA_LIMIT else "")


def select_shell_replica(
    replicas: Any,
    requested: Optional[str],
    workload: str,
    *,
    stopped_reasons: FrozenSet[str] = NON_EXECUTABLE_REPLICA_REASONS,
    prefer_newest: bool = False,
) -> str:
    """Return the requested replica, or the one a shell opens in by default.

    ``workload`` names the resource in messages, e.g. ``"pod my-pod"``. By
    default exactly one running replica must exist. With ``prefer_newest``
    the most recently created replica is used instead, as the dashboard's
    Pod card does.
    """
    if not isinstance(replicas, list):
        raise ShellUnavailable(
            f"The server returned an invalid replica list for {workload}."
        )
    ids, live, newest, newest_at = [], [], None, None
    for item in replicas:
        rid = _replica_id(item)
        if rid is None or rid in ids:
            raise ShellUnavailable(
                f"The server returned invalid or duplicate replica IDs for {workload}."
            )
        ids.append(rid)
        if not _stopped(item, stopped_reasons):
            live.append(rid)
        if newest_at is None or _created_at(item) > newest_at:
            newest, newest_at = rid, _created_at(item)
    if requested is not None or prefer_newest:
        target = requested if requested is not None else newest
        if target is None:
            raise ShellUnavailable(f"{_sentence(workload)} has no replicas.")
        if target not in ids:
            raise ShellUnavailable(
                f"Replica {target!r} does not belong to {workload}."
                + (f" Current replicas: {_listed(ids)}." if ids else "")
            )
        if target not in live:
            raise ShellUnavailable(
                f"Replica {target!r} of {workload} has stopped and cannot run a shell."
            )
        return target
    if not live:
        raise ShellUnavailable(f"{_sentence(workload)} has no running replicas.")
    if len(live) != 1:
        raise ShellUnavailable(
            f"{_sentence(workload)} has {len(live)} running replicas. Select one"
            f" with --replica: {_listed(live)}."
        )
    return live[0]
