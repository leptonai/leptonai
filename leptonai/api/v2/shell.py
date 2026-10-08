"""Choose the replica a workspace ``/shell`` session should exec into.

The dashboard terminal and the TUI never offer a replica whose container is
gone; this module applies the same rule to the raw replica list so callers
see the readiness field the typed ``Replica`` model drops.
"""

from typing import Any, List, Optional


# Readiness reasons reported once a replica's container can no longer run.
NON_EXECUTABLE_REPLICA_REASONS = frozenset(
    {"Completed", "Failed", "Deleted", "Terminated"}
)
_LISTED_REPLICA_LIMIT = 10


class ShellUnavailable(RuntimeError):
    """No shell target could be selected; the message is user-facing."""


def _replica_id(item: Any) -> Optional[str]:
    if not isinstance(item, dict):
        return None
    metadata = item.get("metadata")
    rid = metadata.get("id") if isinstance(metadata, dict) else None
    if rid is None:
        rid = item.get("id")
    return rid if isinstance(rid, str) and rid.strip() else None


def _executable(item: dict) -> bool:
    status = item.get("status")
    readiness = status.get("readiness_issue") if isinstance(status, dict) else None
    reason = readiness.get("reason") if isinstance(readiness, dict) else None
    return reason not in NON_EXECUTABLE_REPLICA_REASONS


def _sentence(text: str) -> str:
    return text[:1].upper() + text[1:]


def _listed(ids: List[str]) -> str:
    shown = ", ".join(ids[:_LISTED_REPLICA_LIMIT])
    return shown + (", ..." if len(ids) > _LISTED_REPLICA_LIMIT else "")


def select_shell_replica(replicas: Any, requested: Optional[str], workload: str) -> str:
    """Return the requested replica, or the only one that can run a shell.

    ``workload`` names the resource in messages, e.g. ``"pod my-pod"``.
    """
    if not isinstance(replicas, list):
        raise ShellUnavailable(
            f"The server returned an invalid replica list for {workload}."
        )
    ids, live = [], []
    for item in replicas:
        rid = _replica_id(item)
        if rid is None or rid in ids:
            raise ShellUnavailable(
                f"The server returned invalid or duplicate replica IDs for {workload}."
            )
        ids.append(rid)
        if _executable(item):
            live.append(rid)
    if requested is not None:
        if requested not in ids:
            raise ShellUnavailable(
                f"Replica {requested!r} does not belong to {workload}."
                + (f" Current replicas: {_listed(ids)}." if ids else "")
            )
        if requested not in live:
            raise ShellUnavailable(
                f"Replica {requested!r} of {workload} has stopped and cannot run a"
                " shell."
            )
        return requested
    if not live:
        raise ShellUnavailable(f"{_sentence(workload)} has no running replicas.")
    if len(live) != 1:
        raise ShellUnavailable(
            f"{_sentence(workload)} has {len(live)} running replicas. Select one"
            f" with --replica: {_listed(live)}."
        )
    return live[0]
