"""CLI commands for workspace Slurm resources."""

import json
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import click
from rich.table import Table

from ..api.v2.client import APIClient
from ..api.v2.types.slurm import (
    LeptonSlurmCluster,
    LeptonSlurmDevPod,
    SlurmJobAttempt,
    WorkspaceSlurmJob,
    WorkspaceSlurmJobList,
)
from .log import _preprocess_time
from .util import click_group, colorize_state, console, make_name_id_cell


OUTPUT_FORMAT = click.Choice(("table", "json"), case_sensitive=False)


def _model_dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True, exclude_none=True)
    if hasattr(value, "dict"):
        return value.dict(by_alias=True, exclude_none=True)
    if isinstance(value, list):
        return [_model_dump(item) for item in value]
    if isinstance(value, tuple):
        return [_model_dump(item) for item in value]
    if isinstance(value, dict):
        return {key: _model_dump(item) for key, item in value.items()}
    return value


def _print_json(value: Any) -> None:
    click.echo(json.dumps(_model_dump(value), indent=2, sort_keys=True, default=str))


def _epoch_seconds(value: Any) -> Optional[float]:
    if value in (None, "", 0, "0"):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    absolute = abs(numeric)
    if absolute >= 100_000_000_000_000_000:
        return numeric / 1_000_000_000
    if absolute >= 100_000_000_000_000:
        return numeric / 1_000_000
    if absolute >= 100_000_000_000:
        return numeric / 1_000
    return numeric


def _format_time(value: Any) -> str:
    seconds = _epoch_seconds(value)
    if seconds is not None:
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )
        except (OSError, OverflowError, ValueError):
            return str(value)
    if value in (None, "", 0, "0"):
        return "-"
    return str(value)


def _format_time_cell(value: Any) -> str:
    """Format an epoch of any precision as a local-time table cell.

    Matches the two-line 'YYYY-MM-DD\\nHH:MM:SS' layout used by `lep job list`.
    """
    seconds = _epoch_seconds(value)
    if seconds is None:
        return "-"
    try:
        return datetime.fromtimestamp(seconds).strftime("%Y-%m-%d\n%H:%M:%S")
    except (OSError, OverflowError, ValueError):
        return str(value)


# Slurm-only terminal states that must render red like Error/Failed do in
# colorize_state.
_SLURM_FAILURE_STATES = {
    "BootFail",
    "Deadline",
    "NodeFail",
    "OutOfMemory",
    "Timeout",
    "Unrecoverable",
}


def _normalize_state(value: Any) -> str:
    """Map raw Slurm states (RUNNING, NODE_FAIL) to CLI casing (Running, NodeFail)."""
    if value is None:
        return "-"
    text = str(getattr(value, "value", value)).strip()
    if not text:
        return "-"
    if text.isupper():
        return "".join(part.capitalize() for part in text.replace("-", "_").split("_"))
    return text


def _state_cell(*candidates: Any) -> str:
    """Colorize the first non-empty state, consistent with `lep job list`."""
    state = next((value for value in candidates if value), None)
    text = _normalize_state(state)
    if text in _SLURM_FAILURE_STATES:
        return f"[red]{text}[/]"
    return colorize_state(text)


def _safe_dashboard_url(api: Any, view: str, **kwargs: Any) -> Optional[str]:
    """Build a dashboard URL for a table link; never fail table rendering."""
    if api is None:
        return None
    try:
        return api.dashboard_url(view, **kwargs)
    except Exception:
        return None


def _devpod_cluster(
    item: LeptonSlurmDevPod, clusters: Iterable[LeptonSlurmCluster]
) -> Optional[LeptonSlurmCluster]:
    """Resolve a Dev Pod's cluster by its recorded cluster name.

    A Dev Pod ID has its own Kubernetes namespace, which is not necessarily
    the Slurm cluster namespace (for example ``slurm-tf-test`` versus
    ``slurm``). The canonical dashboard route must therefore come from the
    cluster record rather than be synthesized from the Dev Pod ID.
    """
    cluster_name = (item.spec.slurm_cluster_name or "").strip()
    if not cluster_name:
        return None
    matches = [cluster for cluster in clusters if cluster.metadata.name == cluster_name]
    if len(matches) != 1 or not matches[0].metadata.id_:
        return None
    return matches[0]


def _require_devpod_cluster(
    item: LeptonSlurmDevPod, clusters: Iterable[LeptonSlurmCluster]
) -> LeptonSlurmCluster:
    cluster = _devpod_cluster(item, clusters)
    if cluster is None:
        raise ValueError(
            "The Slurm Dev Pod's recorded cluster name did not resolve to one "
            "canonical cluster in this workspace."
        )
    return cluster


def _devpod_dashboard_url(
    api: Any,
    item: LeptonSlurmDevPod,
    clusters: Iterable[LeptonSlurmCluster],
) -> Optional[str]:
    cluster = _devpod_cluster(item, clusters)
    if cluster is None:
        return None
    return _safe_dashboard_url(api, "devpods", cluster_id=cluster.metadata.id_)


def _reported_devpod_ssh_command(item: LeptonSlurmDevPod) -> Optional[str]:
    command = item.status.ssh_command if item.status else None
    return command if command and command.strip() else None


def _web_ui_link(url: Optional[str]) -> str:
    if not url:
        return "-"
    return f"[link={url}][blue underline]Open in web UI ↗[/][/link]"


def _format_resources(cpus: Any, gpus: Any, memory_mb: Any) -> str:
    return f"{cpus or 0}C / {gpus or 0}G / {memory_mb or 0}MiB"


def _format_duration(start: Any, end: Any) -> str:
    start_seconds = _epoch_seconds(start)
    end_seconds = _epoch_seconds(end)
    if start_seconds is None or end_seconds is None or end_seconds < start_seconds:
        return "-"
    duration = int(end_seconds - start_seconds)
    hours, remainder = divmod(duration, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _diagnosis(reason: Optional[str], error: Optional[str]) -> str:
    return error or reason or "-"


def _filter_clusters(
    clusters: Iterable[LeptonSlurmCluster],
    *,
    names: Iterable[str] = (),
    statuses: Iterable[str] = (),
) -> List[LeptonSlurmCluster]:
    """Apply the dashboard's client-side cluster name and status filters."""
    name_filters = tuple(value.strip().casefold() for value in names if value.strip())
    status_filters = {value.strip().casefold() for value in statuses if value.strip()}
    filtered = []
    for item in clusters:
        name = (item.metadata.name or "").casefold()
        state = (
            str(getattr(item.status.state, "value", item.status.state))
            .strip()
            .casefold()
            if item.status and item.status.state
            else ""
        )
        if name_filters and not any(value in name for value in name_filters):
            continue
        if status_filters and state not in status_filters:
            continue
        filtered.append(item)
    return filtered


def _print_clusters_table(
    clusters: Iterable[LeptonSlurmCluster], *, api: Any = None
) -> None:
    table = Table(title="Slurm Clusters", show_header=True, show_lines=True)
    table.add_column("Name / ID")
    table.add_column("State")
    table.add_column("Login Nodes")
    table.add_column("Dev Pods")
    table.add_column("Diagnosis")
    for item in clusters:
        status = item.status
        spec = item.spec
        login_nodes = [] if status is None else status.login_node_addresses
        devpods = None if spec is None else spec.dev_pods_config
        link = (
            _safe_dashboard_url(api, "detail", cluster_id=item.metadata.id_)
            if item.metadata.id_
            else None
        )
        table.add_row(
            make_name_id_cell(item.metadata.name, item.metadata.id_, link=link),
            _state_cell(status.state if status else None),
            ", ".join(login_nodes) or "-",
            "Enabled" if devpods and devpods.enabled else "Disabled",
            _diagnosis(
                status.reason if status else None, status.error if status else None
            ),
        )
    console.print(table)


def _print_failed_clusters(failed_clusters: Dict[str, str]) -> None:
    if not failed_clusters:
        return
    console.print("[yellow]Some clusters could not be queried:[/yellow]")
    for cluster_name, error in sorted(failed_clusters.items()):
        console.print(f"  {cluster_name}: {error}")


def _job_cluster_cell(job: WorkspaceSlurmJob, api: Any = None) -> str:
    if not job.slurm_cluster:
        return "-"
    label = job.slurm_cluster.name or job.slurm_cluster.id_ or "-"
    link = (
        _safe_dashboard_url(api, "detail", cluster_id=job.slurm_cluster.id_)
        if job.slurm_cluster.id_
        else None
    )
    return f"[link={link}]{label}[/link]" if link else label


def _print_jobs_table(result: WorkspaceSlurmJobList, *, api: Any = None) -> None:
    table = Table(
        title=f"Slurm Jobs ({len(result.jobs)} shown / {result.total} total)",
        show_header=True,
        show_lines=True,
    )
    table.add_column("Cluster", style="cyan")
    table.add_column("Name / ID")
    table.add_column("State")
    table.add_column("User")
    table.add_column("Partition / QoS")
    table.add_column("CPU / GPU / Memory", justify="right")
    table.add_column("Submitted")
    for item in result.jobs:
        job_id = str(item.spec.job_id) if item.spec.job_id is not None else None
        link = (
            _safe_dashboard_url(
                api,
                "overview",
                cluster_id=item.slurm_cluster.id_,
                job_id=job_id,
            )
            if item.slurm_cluster and item.slurm_cluster.id_ and job_id
            else None
        )
        table.add_row(
            _job_cluster_cell(item, api),
            make_name_id_cell(item.metadata.name, job_id, link=link),
            _state_cell(item.status.job_state, item.status.state),
            item.metadata.created_by or item.metadata.owner or "-",
            f"{item.status.partition or '-'} / {item.status.qos or '-'}",
            _format_resources(item.spec.cpus, item.spec.gpus, item.spec.memory_mb),
            _format_time_cell(item.metadata.created_at),
        )
    console.print(table)
    _print_failed_clusters(result.failed_clusters)


def _print_attempts_table(
    attempts: Iterable[SlurmJobAttempt], *, include_steps: bool
) -> None:
    table = Table(title="Slurm Job Attempts", show_header=True, show_lines=True)
    table.add_column("Attempt / Step", style="cyan", min_width=11, no_wrap=True)
    table.add_column("State", min_width=9, no_wrap=True)
    table.add_column("Nodes")
    table.add_column("CPU / GPU / Memory", justify="right")
    table.add_column("Started")
    table.add_column("Duration")
    table.add_column("Return Code")
    for attempt in attempts:
        table.add_row(
            f"Attempt {attempt.attempt}",
            _state_cell(attempt.state),
            ", ".join(attempt.nodes) or "-",
            _format_resources(attempt.cpus, attempt.gpus, attempt.memory_mb),
            _format_time_cell(attempt.start_at or attempt.submit_at),
            _format_duration(attempt.start_at, attempt.end_at),
            "-" if attempt.return_code is None else str(attempt.return_code),
        )
        if include_steps:
            for step in attempt.steps:
                table.add_row(
                    f"{attempt.attempt}/{step.id_ or step.name or '-'}",
                    _state_cell(step.state),
                    ", ".join(step.nodes) or "-",
                    _format_resources(step.cpus, step.gpus, step.memory_mb),
                    _format_time_cell(step.start_at or step.submit_at),
                    _format_duration(step.start_at, step.end_at),
                    "-" if step.return_code is None else str(step.return_code),
                )
    console.print(table)


def _print_devpods_table(
    devpods: Iterable[LeptonSlurmDevPod],
    *,
    api: Any = None,
    clusters: Iterable[LeptonSlurmCluster] = (),
) -> None:
    clusters = list(clusters)
    table = Table(title="Slurm Dev Pods", show_header=True, show_lines=True)
    table.add_column("Name / ID", overflow="fold")
    table.add_column("Cluster")
    table.add_column("State")
    table.add_column("User")
    table.add_column("CPU Req/Limit")
    table.add_column("Mem Req/Limit")
    table.add_column("Image")
    table.add_column("SSH")
    for item in devpods:
        status = item.status
        resources = status.container_resources if status else None
        requests = resources.requests if resources else None
        limits = resources.limits if resources else None
        devpod_id = item.metadata.id_
        link = _devpod_dashboard_url(api, item, clusters)
        table.add_row(
            make_name_id_cell(item.metadata.name, devpod_id, link=link),
            item.spec.slurm_cluster_name,
            _state_cell(status.state if status else None),
            (status.username if status else None) or "-",
            f"{(requests.cpu if requests else None) or '-'}/"
            f"{(limits.cpu if limits else None) or '-'}",
            f"{(requests.memory if requests else None) or '-'}/"
            f"{(limits.memory if limits else None) or '-'}",
            (status.image_version if status else None) or "-",
            "[green]Ready[/]" if _reported_devpod_ssh_command(item) else "-",
        )
    console.print(table)


def _devpod_detail_table(title: str, rows: Iterable[Tuple[str, str]]) -> Table:
    table = Table(title=title, show_header=False, box=None, padding=(0, 1))
    table.add_column("Field", style="bold", no_wrap=True)
    table.add_column("Value", overflow="fold")
    for label, value in rows:
        table.add_row(label, value)
    return table


def _devpod_profile(item: LeptonSlurmDevPod, cluster: LeptonSlurmCluster) -> Any:
    recorded = item.spec.dev_pod_set_name
    config = cluster.spec.dev_pods_config if cluster.spec else None
    if not recorded or not config:
        return None
    return next((profile for profile in config.sets if profile.name == recorded), None)


def _devpod_resource_value(item: LeptonSlurmDevPod, dimension: str) -> str:
    resources = item.status.container_resources if item.status else None
    requests = resources.requests if resources else None
    value = getattr(requests, dimension, None) if requests else None
    return value or "-"


def _devpod_limit_value(item: LeptonSlurmDevPod, dimension: str) -> str:
    resources = item.status.container_resources if item.status else None
    limits = resources.limits if resources else None
    if limits is None:
        return "-"
    value = getattr(limits, dimension, None)
    return value or "No limit"


def _home_directory_text(cluster: LeptonSlurmCluster) -> str:
    home = cluster.spec.home_dirs_config if cluster.spec else None
    backend = home.storage_backend if home else None
    if backend and backend.host_path is not None:
        path = backend.host_path.path
        qualifier = (
            f"configured on the node at {path}" if path else "configured on a node path"
        )
    elif backend and backend.persistent_volume is not None:
        claim = backend.persistent_volume.claim_name
        qualifier = (
            f"configured on cluster volume {claim}"
            if claim
            else "configured on a cluster volume"
        )
    else:
        qualifier = "configured on the cluster file system"
    return f"/home ({qualifier})"


def _scratch_text(cluster: LeptonSlurmCluster) -> str:
    login = cluster.spec.login_nodes_config if cluster.spec else None
    qualifier = (
        "configured as node-local storage"
        if login and login.node_scratch_path
        else "held in RAM"
    )
    return f"/raid ({qualifier})"


def _shared_storage_text(cluster: LeptonSlurmCluster) -> str:
    storage = cluster.spec.cluster_shared_storage_config if cluster.spec else None
    paths = storage.shared_storage_paths if storage else []
    visible = []
    for path in paths:
        if "login" in path.excluded_node_group_types or not path.mount_path:
            continue
        visible.append(
            f"{path.mount_path} (read-only)" if path.read_only else path.mount_path
        )
    return "\n".join(visible) or "-"


def _bastion_text(cluster: LeptonSlurmCluster) -> str:
    devpods = cluster.spec.dev_pods_config if cluster.spec else None
    bastion = devpods.bastion if devpods else None
    if not bastion or bastion.enabled is not True:
        return "Not enabled"
    login = cluster.spec.login_nodes_config if cluster.spec else None
    qualifier = (
        "reachable from the networks this cluster allows"
        if bastion.use_load_balancer is True and login and login.source_cidrs
        else "reachable from this cluster's private network"
    )
    return f"Enabled ({qualifier})"


def _print_devpod_detail(
    item: LeptonSlurmDevPod, cluster: LeptonSlurmCluster, *, api: Any = None
) -> None:
    """Render the dashboard's Configuration, Identity, and Connect facts."""
    status = item.status
    cluster = _require_devpod_cluster(item, [cluster])
    cluster_id = cluster.metadata.id_
    profile_name = item.spec.dev_pod_set_name
    profile = _devpod_profile(item, cluster)
    if profile_name and profile is None:
        profile_text = f"{profile_name} (not in current cluster configuration)"
    else:
        profile_text = profile_name or "-"

    summary = Table.grid(padding=(0, 1))
    summary.add_column()
    summary.add_column()
    summary.add_row(
        make_name_id_cell(item.metadata.name, item.metadata.id_),
        _state_cell(status.state if status else None),
    )
    console.print(summary)

    state = _normalize_state(status.state if status else None)
    if state == "NotReady":
        console.print(
            "[yellow]Dev pod not ready:[/] "
            + (
                (status.reason if status else None)
                or "The platform has not reported a reason yet."
            )
        )
    elif state in ("Error", "Unrecoverable"):
        console.print(
            "[red]Dev pod failed:[/] "
            + ((status.error if status else None) or "The dev pod failed to start.")
        )

    console.print(
        _devpod_detail_table(
            "Configuration",
            (
                ("Cluster", cluster_id),
                ("Environment profile", profile_text),
                (
                    "Profile node group",
                    (profile.node_group_id if profile else None) or "-",
                ),
                ("Image version", (status.image_version if status else None) or "-"),
                ("CPU request", _devpod_resource_value(item, "cpu")),
                ("Memory request", _devpod_resource_value(item, "memory")),
                ("CPU limit", _devpod_limit_value(item, "cpu")),
                ("Memory limit", _devpod_limit_value(item, "memory")),
                ("Bastion", _bastion_text(cluster)),
                ("Home directory", _home_directory_text(cluster)),
                ("Scratch", _scratch_text(cluster)),
                ("Shared storage", _shared_storage_text(cluster)),
            ),
        )
    )
    console.print(
        _devpod_detail_table(
            "Identity",
            (
                ("Cluster user", (status.username if status else None) or "-"),
                ("ID", item.metadata.id_ or "-"),
                ("UUID", item.metadata.uuid or "-"),
                ("Created", _format_time(item.metadata.created_at)),
                ("Created by", item.metadata.created_by or "-"),
                ("Owner", item.metadata.owner or "-"),
            ),
        )
    )

    devpods = cluster.spec.dev_pods_config if cluster.spec else None
    bastion = devpods.bastion if devpods else None
    ssh_command = _reported_devpod_ssh_command(item)
    if bastion and bastion.enabled is True:
        ssh_text = ssh_command or "Available when the platform reports the command"
    else:
        ssh_text = "Not enabled"
    shell_text = (
        shlex.join(["lep", "slurm", "devpod", "shell", "--id", item.metadata.id_])
        if state == "Ready" and item.metadata.id_
        else "Available when the Dev Pod is ready"
    )
    console.print(
        _devpod_detail_table(
            "Connect",
            (
                ("Dev Pod shell", shell_text),
                ("SSH via bastion", ssh_text),
                (
                    "Dashboard",
                    _web_ui_link(_devpod_dashboard_url(api, item, [cluster])),
                ),
            ),
        )
    )


def _extract_log_entries(payload: Any) -> List[Tuple[Optional[int], str]]:
    """Flatten a Loki query-range response into timestamp/message tuples."""
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return [(None, payload)]
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    streams = data.get("result", []) if isinstance(data, dict) else data
    if not isinstance(streams, list):
        return []

    entries: List[Tuple[Optional[int], str]] = []
    for stream in streams:
        values = stream.get("values", []) if isinstance(stream, dict) else []
        for value in values:
            if not isinstance(value, (list, tuple)) or len(value) < 2:
                continue
            try:
                timestamp = int(value[0])
            except (TypeError, ValueError):
                timestamp = None
            message = value[1]
            if not isinstance(message, str):
                message = json.dumps(message, sort_keys=True, default=str)
            entries.append((timestamp, message))
    entries.sort(key=lambda entry: entry[0] if entry[0] is not None else -1)
    return entries


def _print_log_entries(
    entries: Iterable[Tuple[Optional[int], str]], *, timestamps: bool
) -> None:
    for timestamp, message in entries:
        if timestamps and timestamp is not None:
            click.echo(f"{_format_time(timestamp)} {message}")
        else:
            click.echo(message)


def _job_identifier(item: WorkspaceSlurmJob) -> str:
    if item.spec is not None and item.spec.job_id is not None:
        return str(item.spec.job_id)
    return str(item.metadata.id_ or "-")


def _job_cluster_id(item: WorkspaceSlurmJob) -> str:
    if item.slurm_cluster is None or not item.slurm_cluster.id_:
        raise click.ClickException(
            f"Job {_job_identifier(item)} has no cluster ID in the API response."
        )
    return item.slurm_cluster.id_


def _validate_name_id_selector(name: Optional[str], id: Optional[str]) -> None:
    if not name and not id:
        raise click.UsageError("You must provide either --name or --id.")
    if name and id:
        raise click.UsageError(
            "You cannot provide both --name and --id. Please specify only one."
        )


def _resolve_cluster(
    api: Any, cluster: str, *, clusters: Optional[List[LeptonSlurmCluster]] = None
) -> str:
    """Resolve a cluster NAME or NAMESPACE/NAME to the canonical ID.

    Fails loudly when nothing matches: the workspace jobs route skips
    unknown cluster filters silently, which would read as "job not found".
    """
    if clusters is None:
        clusters = api.list_clusters()
    if "/" in cluster:
        matches = [item for item in clusters if item.metadata.id_ == cluster]
    else:
        matches = [item for item in clusters if item.metadata.name == cluster]
    if len(matches) == 1:
        return str(matches[0].metadata.id_)
    if not matches:
        console.print(f"Slurm cluster [red]{cluster}[/] was not found.")
        if clusters:
            console.print("Available clusters:")
            for item in clusters:
                console.print(f"  {item.metadata.id_}")
        sys.exit(1)
    console.print(f"[red]{cluster}[/] matches several clusters; use NAMESPACE/NAME:")
    for item in matches:
        console.print(f"  {item.metadata.id_}")
    sys.exit(1)


def _resolve_jobs(
    api: Any,
    *,
    name: Optional[str],
    id: Optional[str],
    cluster_id: Optional[str],
    include_archived: bool,
) -> List[Tuple[str, Any]]:
    """Resolve --name/--id to (cluster ID, job) pairs.

    With a resolved cluster ID the cluster-scoped jobs route is queried
    directly; otherwise the workspace-wide route fans out across clusters.
    The server-side ``q`` filter narrows candidates by job ID or name
    substring; exact matching happens client-side.
    """
    query = name or id or ""
    mode = "alive_and_archive" if include_archived else "alive_only"
    candidates: List[Tuple[Optional[str], Any]] = []
    failed_clusters: Dict[str, str] = {}
    if cluster_id:
        jobs = api.list_cluster_jobs(cluster_id, job_query_mode=mode, q=query)
        candidates.extend((cluster_id, item) for item in jobs)
    else:
        result = api.list_jobs(job_query_mode=mode, q=query)
        candidates.extend(
            (item.slurm_cluster.id_ if item.slurm_cluster else None, item)
            for item in result.jobs
        )
        failed_clusters.update(result.failed_clusters)

    if id:
        matches = [pair for pair in candidates if _job_identifier(pair[1]) == id]
    else:
        matches = [pair for pair in candidates if pair[1].metadata.name == name]
    if matches:
        return [(owner or _job_cluster_id(item), item) for owner, item in matches]

    scope = "alive or archived" if include_archived else "alive"
    search_type = "name" if name else "ID"
    console.print(f"No {scope} Slurm job found for [red]{search_type}: {query}[/].")
    if not include_archived:
        console.print(
            "Archived jobs are skipped by default; retry with"
            " [green]--include-archived[/]."
        )
    _print_failed_clusters(failed_clusters)
    sys.exit(1)


def _resolve_single_job(
    api: Any,
    *,
    name: Optional[str],
    id: Optional[str],
    cluster_id: Optional[str],
    include_archived: bool,
) -> Tuple[str, Any]:
    matches = _resolve_jobs(
        api, name=name, id=id, cluster_id=cluster_id, include_archived=include_archived
    )
    if len(matches) == 1:
        return matches[0]
    console.print(
        f"[red]{name or id}[/] matches {len(matches)} Slurm jobs; disambiguate"
        " with [green]--cluster NAMESPACE/NAME[/] or [green]--id[/]:"
    )
    table = Table(show_header=True)
    table.add_column("Cluster", style="cyan")
    table.add_column("Job ID")
    table.add_column("Name")
    table.add_column("State")
    for owner, item in matches:
        table.add_row(
            owner,
            _job_identifier(item),
            item.metadata.name or "-",
            _state_cell(item.status.job_state, item.status.state),
        )
    console.print(table)
    sys.exit(1)


def _job_resolution_options(command):
    """Attach the shared job selection flags (mirrors `lep job get`)."""
    command = click.option(
        "--include-archived",
        "-ia",
        is_flag=True,
        default=False,
        help="Include archived jobs when resolving name/id.",
    )(command)
    command = click.option(
        "--cluster",
        "cluster",
        "-c",
        help=(
            "Cluster NAME or NAMESPACE/NAME; verified first, then the job"
            " is looked up inside that cluster only."
        ),
    )(command)
    command = click.option("--id", "-i", help="Slurm job id", type=str)(command)
    command = click.option("--name", "-n", help="Job name", type=str)(command)
    return command


def _devpod_resolution_options(command):
    """Attach shared Dev Pod selectors; cluster optionally scopes name/id."""
    command = click.option(
        "--cluster",
        "cluster",
        "-c",
        help=(
            "Owning cluster NAME or NAMESPACE/NAME; may be used alone or to "
            "scope --name/--id."
        ),
    )(command)
    command = click.option("--id", "-i", help="Dev Pod ID", type=str)(command)
    command = click.option("--name", "-n", help="Dev Pod name", type=str)(command)
    return command


def _validate_devpod_selector(
    name: Optional[str], id: Optional[str], cluster: Optional[str]
) -> None:
    if not any((name, id, cluster)):
        raise click.UsageError("You must provide one of --name, --id, or --cluster.")
    if name and id:
        raise click.UsageError("You cannot provide both --name and --id.")


def _resolve_devpod_selection(
    api: Any,
    name: Optional[str],
    id: Optional[str],
    cluster: Optional[str],
) -> LeptonSlurmDevPod:
    """Resolve name/id globally or within an optional validated cluster."""
    _validate_devpod_selector(name, id, cluster)
    if not cluster:
        return api.resolve_devpod(name or id)
    cluster_id = _resolve_cluster(api, cluster)
    return api.resolve_devpod(name or id, cluster=cluster_id)


@click_group()
def slurm():
    """Inspect Slurm clusters/jobs and manage your Slurm Dev Pods."""


@slurm.group()
def cluster():
    """Inspect Slurm clusters and start login-node shells."""


@cluster.command(name="list")
@click.option(
    "--name",
    "names",
    "-n",
    multiple=True,
    help="Filter by cluster name substring (case-insensitive; repeatable).",
)
@click.option(
    "--status",
    "statuses",
    "-s",
    multiple=True,
    help="Filter by exact cluster status (case-insensitive; repeatable).",
)
@click.option("--output", "output_format", "-o", type=OUTPUT_FORMAT, default="table")
def list_clusters(
    names: Tuple[str, ...], statuses: Tuple[str, ...], output_format: str
) -> None:
    """List Slurm clusters, optionally filtering by name and status."""
    api = APIClient().slurm
    clusters = _filter_clusters(api.list_clusters(), names=names, statuses=statuses)
    if output_format == "json":
        _print_json(clusters)
    else:
        _print_clusters_table(clusters, api=api)


@cluster.command(name="get")
@click.option("--name", "-n", help="Cluster name", type=str)
@click.option("--id", "-i", help="Canonical NAMESPACE/NAME cluster ID", type=str)
def get_cluster(name: Optional[str], id: Optional[str]) -> None:
    """Get a Slurm cluster by --name or --id (NAMESPACE/NAME)."""
    _validate_name_id_selector(name, id)
    api = APIClient().slurm
    clusters = api.list_clusters()
    cluster_id = _resolve_cluster(api, id or name, clusters=clusters)
    _print_json(next(c for c in clusters if c.metadata.id_ == cluster_id))


@cluster.command(name="events")
@click.option("--name", "-n", help="Cluster name", type=str)
@click.option("--id", "-i", help="Canonical NAMESPACE/NAME cluster ID", type=str)
@click.option("--limit", type=click.IntRange(min=1), default=100, show_default=True)
@click.option("--type", "event_type", help="Filter by cluster event type.")
@click.option("--output", "output_format", "-o", type=OUTPUT_FORMAT, default="table")
def cluster_events(
    name: Optional[str],
    id: Optional[str],
    limit: int,
    event_type: Optional[str],
    output_format: str,
) -> None:
    """Show lifecycle and administration events for a cluster.

    Select the cluster by --name or --id (NAMESPACE/NAME).
    """
    _validate_name_id_selector(name, id)
    api = APIClient().slurm
    cluster_id = _resolve_cluster(api, id or name)
    events = api.list_cluster_events(cluster_id, limit=limit, event_type=event_type)
    if output_format == "json":
        _print_json(events)
        return
    table = Table(title=f"Slurm Cluster Events: {cluster_id}")
    table.add_column("Timestamp")
    table.add_column("Type", style="cyan")
    table.add_column("User")
    table.add_column("Message")
    for event in events:
        table.add_row(
            event.timestamp or "-",
            event.type_ or "-",
            event.user or "-",
            event.message or "-",
        )
    console.print(table)


# Deliberately NOT registered on the cluster group: direct SSH to login
# nodes is not reachable in most deployments yet. Use `lep slurm cluster
# shell` instead; re-register with cluster.add_command(ssh_cluster) once
# login-node connectivity is generally available.
@click.command(name="ssh", context_settings={"ignore_unknown_options": True})
@click.option("--name", "-n", help="Cluster name", type=str)
@click.option("--id", "-i", help="Canonical NAMESPACE/NAME cluster ID", type=str)
@click.option("--user", "-u", "ssh_user", help="Username on the login node.")
@click.option(
    "--login-node",
    help="Login node address to connect to; defaults to the cluster's first one.",
)
@click.argument("ssh_args", nargs=-1, type=click.UNPROCESSED)
@click.option(
    "--print-only", is_flag=True, help="Print the SSH command without running it."
)
def ssh_cluster(
    name: Optional[str],
    id: Optional[str],
    ssh_user: Optional[str],
    login_node: Optional[str],
    ssh_args: Tuple[str, ...],
    print_only: bool,
) -> None:
    """SSH to a login node of a Slurm cluster.

    Select the cluster by --name or --id (NAMESPACE/NAME). Without --user
    the local SSH configuration decides the login name. Extra SSH options
    can be passed after ``--``.
    """
    _validate_name_id_selector(name, id)
    api = APIClient().slurm
    clusters = api.list_clusters()
    cluster_id = _resolve_cluster(api, id or name, clusters=clusters)
    item = next(c for c in clusters if c.metadata.id_ == cluster_id)
    addresses = item.status.login_node_addresses if item.status else []
    if not addresses:
        state = _normalize_state(item.status.state if item.status else None)
        console.print(
            f"Slurm cluster [red]{cluster_id}[/] reports no login node addresses"
            f" (state: {state})."
        )
        sys.exit(1)
    if login_node and login_node not in addresses:
        console.print(f"Login node [red]{login_node}[/] is not on {cluster_id}.")
        console.print("Available login nodes:")
        for address in addresses:
            console.print(f"  {address}")
        sys.exit(1)
    address = login_node or addresses[0]
    destination = f"{ssh_user}@{address}" if ssh_user else address
    argv = ["ssh", destination, *ssh_args]
    click.echo(shlex.join(argv))
    if print_only:
        return
    completed = subprocess.run(argv, check=False)
    if completed.returncode:
        raise click.exceptions.Exit(completed.returncode)


@cluster.command(name="shell")
@click.option("--name", "-n", help="Cluster name", type=str)
@click.option("--id", "-i", help="Canonical NAMESPACE/NAME cluster ID", type=str)
def shell_cluster(name: Optional[str], id: Optional[str]) -> None:
    """Open an interactive shell on a login node of a Slurm cluster.

    The session is tunnelled through the workspace API over HTTPS (the
    same path the dashboard terminal uses), so it works wherever `lep`
    works. The shell runs as your workspace user on the login node.
    """
    # Local import keeps websocket-client off the CLI startup path.
    from .ws_shell import ensure_interactive_terminal, run_ws_shell

    _validate_name_id_selector(name, id)
    ensure_interactive_terminal()
    api = APIClient().slurm
    cluster_id = _resolve_cluster(api, id or name)
    console.print(
        f"Opening a login-node shell on [green]{cluster_id}[/]"
        " (type `exit` or press Ctrl-D to leave)..."
    )
    exit_code = run_ws_shell(api.shell_connection(cluster_id))
    if exit_code:
        raise click.exceptions.Exit(exit_code)


@slurm.group()
def job():
    """Inspect jobs submitted through Slurm."""


@job.command(name="list")
@click.option(
    "--cluster",
    "cluster_names",
    "-c",
    multiple=True,
    help="Filter by cluster NAME or NAMESPACE/NAME; repeatable.",
)
@click.option(
    "--status",
    "statuses",
    "-s",
    multiple=True,
    help="Filter by job status; repeatable.",
)
@click.option(
    "--include-archived",
    "-ia",
    is_flag=True,
    default=False,
    help="Include archived jobs in the list.",
)
@click.option("--query", "q", "-q", help="Filter by job name substring or job ID.")
@click.option("--created-by", multiple=True, help="Creator email; repeatable.")
@click.option("--output", "output_format", "-o", type=OUTPUT_FORMAT, default="table")
def list_jobs(
    cluster_names: Tuple[str, ...],
    statuses: Tuple[str, ...],
    include_archived: bool,
    q: Optional[str],
    created_by: Tuple[str, ...],
    output_format: str,
) -> None:
    """List Slurm jobs across one or more clusters."""
    mode = "alive_and_archive" if include_archived else "alive_only"
    api = APIClient().slurm
    resolved_clusters: Optional[List[str]] = None
    if cluster_names:
        clusters = api.list_clusters()
        resolved_clusters = [
            _resolve_cluster(api, value, clusters=clusters) for value in cluster_names
        ]
    result = api.list_jobs(
        cluster_names=resolved_clusters,
        job_query_mode=mode,
        q=q,
        status=list(statuses) or None,
        created_by=list(created_by) or None,
    )
    if output_format == "json":
        _print_json(result)
    else:
        _print_jobs_table(result, api=api)


@job.command(name="get")
@_job_resolution_options
@click.option(
    "--raw-slurm",
    is_flag=True,
    help="Return the untranslated slurmrestd response when supported.",
)
def get_job(
    name: Optional[str],
    id: Optional[str],
    cluster: Optional[str],
    include_archived: bool,
    raw_slurm: bool,
) -> None:
    """Get a Slurm job by --id or --name.

    The owning cluster is resolved automatically; prints a JSON array when
    several jobs share the name.
    """
    _validate_name_id_selector(name, id)
    api = APIClient().slurm
    cluster_id = _resolve_cluster(api, cluster) if cluster else None
    if id and cluster_id:
        _print_json(api.get_job(cluster_id, id, slurm_api=raw_slurm))
        return
    matches = _resolve_jobs(
        api, name=name, id=id, cluster_id=cluster_id, include_archived=include_archived
    )
    results = [
        api.get_job(owner, _job_identifier(item), slurm_api=raw_slurm)
        for owner, item in matches
    ]
    _print_json(results[0] if len(results) == 1 else results)


@job.command(name="attempts")
@_job_resolution_options
@click.option("--steps", is_flag=True, help="Include individual Slurm step rows.")
@click.option("--output", "output_format", "-o", type=OUTPUT_FORMAT, default="table")
def job_attempts(
    name: Optional[str],
    id: Optional[str],
    cluster: Optional[str],
    include_archived: bool,
    steps: bool,
    output_format: str,
) -> None:
    """Show requeue attempts and steps for a Slurm job.

    Select the job by --id or --name; the owning cluster is resolved
    automatically.
    """
    _validate_name_id_selector(name, id)
    api = APIClient().slurm
    cluster_id = _resolve_cluster(api, cluster) if cluster else None
    if id and cluster_id:
        events = api.get_job_events(cluster_id, id)
    else:
        owner, item = _resolve_single_job(
            api,
            name=name,
            id=id,
            cluster_id=cluster_id,
            include_archived=include_archived,
        )
        events = api.get_job_events(owner, _job_identifier(item))
    if output_format == "json":
        _print_json(events)
    else:
        _print_attempts_table(events.jobs, include_steps=steps)


@job.command(name="logs")
@_job_resolution_options
@click.option("--attempt", type=click.IntRange(min=0), help="Zero-based attempt.")
@click.option("--step", help="Full Slurm step ID.")
@click.option("--node", help="Filter by Slurm task node.")
@click.option(
    "--log-type",
    type=click.Choice(("all", "stdout", "stderr"), case_sensitive=False),
    default="all",
    show_default=True,
)
@click.option("--query", "query", "-q", help="Filter log lines.")
@click.option("--start", help="UTC time or epoch (seconds/ms/us/ns).")
@click.option("--end", help="UTC time or epoch (seconds/ms/us/ns).")
@click.option("--limit", type=click.IntRange(min=1), default=100, show_default=True)
@click.option("--follow", "follow", "-f", is_flag=True, help="Poll for new log lines.")
@click.option("--timestamps", is_flag=True, help="Prefix each line with its UTC time.")
@click.option(
    "--poll-interval",
    type=click.FloatRange(min=0.1),
    default=2.0,
    show_default=True,
    help="Seconds between requests when following.",
)
def job_logs(
    name: Optional[str],
    id: Optional[str],
    cluster: Optional[str],
    include_archived: bool,
    attempt: Optional[int],
    step: Optional[str],
    node: Optional[str],
    log_type: str,
    query: Optional[str],
    start: Optional[str],
    end: Optional[str],
    limit: int,
    follow: bool,
    timestamps: bool,
    poll_interval: float,
) -> None:
    """Print or follow stdout/stderr logs for a Slurm job.

    Select the job by --id or --name; the owning cluster is resolved
    automatically.
    """
    _validate_name_id_selector(name, id)
    start_ns = _preprocess_time(start, epoch=True) if start else None
    end_ns = _preprocess_time(end, epoch=True) if end else None
    if start_ns is None and end_ns is not None:
        start_ns = end_ns - 5 * 60 * 1_000_000_000
    if start_ns is not None and end_ns is not None and end_ns <= start_ns:
        raise click.UsageError("--end must be later than --start.")
    if follow and end_ns is not None:
        raise click.UsageError("--end cannot be used together with --follow.")
    resolved_log_type = {
        "all": None,
        "stdout": "stdout.log",
        "stderr": "stderr.log",
    }[log_type]
    api = APIClient().slurm
    resolved_cluster = _resolve_cluster(api, cluster) if cluster else None
    if id and resolved_cluster:
        cluster_id, job_id = resolved_cluster, id
    else:
        owner, item = _resolve_single_job(
            api,
            name=name,
            id=id,
            cluster_id=resolved_cluster,
            include_archived=include_archived,
        )
        cluster_id, job_id = owner, _job_identifier(item)

    common = dict(
        job_id=job_id,
        attempt=attempt,
        step=step,
        node=node,
        log_type=resolved_log_type,
        query=query,
        limit=limit,
    )
    if not follow:
        payload = api.get_logs(
            cluster_id,
            start=start_ns,
            end=end_ns,
            direction="backward",
            **common,
        )
        _print_log_entries(_extract_log_entries(payload), timestamps=timestamps)
        return

    cursor = (
        start_ns if start_ns is not None else time.time_ns() - 5 * 60 * 1_000_000_000
    )
    try:
        while True:
            window_end = time.time_ns()
            payload = api.get_logs(
                cluster_id,
                start=cursor,
                end=window_end,
                direction="forward",
                **common,
            )
            entries = _extract_log_entries(payload)
            _print_log_entries(entries, timestamps=timestamps)
            timestamps_seen = [stamp for stamp, _ in entries if stamp is not None]
            if timestamps_seen:
                cursor = max(timestamps_seen) + 1
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        console.print("[dim]Stopped following Slurm logs.[/dim]")


@slurm.group()
def devpod():
    """Manage the current user's Slurm Dev Pods."""


@devpod.command(name="list")
@click.option(
    "--cluster",
    "cluster_names",
    "-c",
    multiple=True,
    help="Filter by cluster NAME or NAMESPACE/NAME; repeatable.",
)
@click.option("--output", "output_format", "-o", type=OUTPUT_FORMAT, default="table")
def list_devpods(cluster_names: Tuple[str, ...], output_format: str) -> None:
    """List Slurm Dev Pods owned by the current user."""
    api = APIClient().slurm
    devpods = api.list_devpods(cluster_names=list(cluster_names) or None)
    if output_format == "json":
        _print_json(devpods)
    else:
        _print_devpods_table(devpods, api=api, clusters=api.list_clusters())


@devpod.command(name="get")
@click.option("--output", "output_format", "-o", type=OUTPUT_FORMAT, default="table")
@_devpod_resolution_options
def get_devpod(
    name: Optional[str],
    id: Optional[str],
    cluster: Optional[str],
    output_format: str,
) -> None:
    """Get your Dev Pod's configuration and identity.

    Select it by --name or --id, optionally scoped by --cluster; the owning
    --cluster may also be used alone. Use --output json for the unmodified API
    record.
    """
    api = APIClient().slurm
    item = _resolve_devpod_selection(api, name, id, cluster)
    if output_format == "json":
        _print_json(item)
        return
    owning_cluster = _require_devpod_cluster(item, api.list_clusters())
    _print_devpod_detail(item, owning_cluster, api=api)


@devpod.command(name="create")
@click.option(
    "--cluster",
    "cluster",
    "-c",
    required=True,
    help="Cluster NAME or NAMESPACE/NAME to create the Dev Pod on.",
)
@click.option("--set", "set_name", help="Dev Pod set configured on the cluster.")
@click.option("--cpu", help="CPU request, for example 4 or 500m.")
@click.option("--memory", help="Memory request, for example 16Gi.")
def create_devpod(
    cluster: str,
    set_name: Optional[str],
    cpu: Optional[str],
    memory: Optional[str],
) -> None:
    """Create your Dev Pod on a Slurm cluster."""
    api = APIClient().slurm
    cluster_id = _resolve_cluster(api, cluster)
    created = api.create_devpod(cluster_id, set_name=set_name, cpu=cpu, memory=memory)
    _print_json(created)


@devpod.command(name="remove")
@_devpod_resolution_options
@click.option("--yes", "assume_yes", "-y", is_flag=True, help="Skip confirmation.")
def remove_devpod(
    name: Optional[str],
    id: Optional[str],
    cluster: Optional[str],
    assume_yes: bool,
) -> None:
    """Remove your Dev Pod by name/id and optional cluster scope."""
    api = APIClient().slurm
    item = _resolve_devpod_selection(api, name, id, cluster)
    devpod_id = item.metadata.id_
    if not devpod_id:
        raise ValueError("The Slurm Dev Pod response did not contain an ID.")
    if not assume_yes:
        click.confirm(f"Remove Slurm Dev Pod {devpod_id}?", abort=True)
    api.delete_devpod(devpod_id)
    console.print(f"[green]Removed Slurm Dev Pod {devpod_id}.[/green]")


@devpod.command(name="ssh", context_settings={"ignore_unknown_options": True})
@_devpod_resolution_options
@click.argument("ssh_args", nargs=-1, type=click.UNPROCESSED)
@click.option(
    "--print-only", is_flag=True, help="Print the SSH command without running it."
)
def ssh_devpod(
    name: Optional[str],
    id: Optional[str],
    cluster: Optional[str],
    ssh_args: Tuple[str, ...],
    print_only: bool,
) -> None:
    """Connect to a Slurm Dev Pod via its cluster bastion.

    Runs the exact SSH command reported by the platform. Select the pod by
    --name or --id, optionally scoped by --cluster; the owning --cluster may
    also be used alone. Extra SSH options can be passed after ``--``.
    """
    api = APIClient().slurm
    item = _resolve_devpod_selection(api, name, id, cluster)
    owning_cluster = _require_devpod_cluster(item, api.list_clusters())
    devpods = owning_cluster.spec.dev_pods_config if owning_cluster.spec else None
    bastion = devpods.bastion if devpods else None
    if not bastion or bastion.enabled is not True:
        raise ValueError(
            "SSH via bastion is not enabled in the Dev Pod's current cluster "
            "configuration. Use `lep slurm devpod shell` instead."
        )
    command = _reported_devpod_ssh_command(item)
    if not command:
        state = item.status.state if item.status else "unknown"
        raise ValueError(
            f"Slurm Dev Pod {item.metadata.id_ or name or id or cluster!r} "
            "has no SSH command "
            f"(state: {state})."
        )
    try:
        argv = shlex.split(command)
    except ValueError as error:
        raise ValueError(f"Invalid SSH command returned by the workspace: {error}")
    if not argv or argv[0] != "ssh":
        raise ValueError("The workspace returned an unsupported Dev Pod SSH command.")
    # The command supplied by the platform already ends in the destination.
    # User-provided SSH options must precede it; appending them would make
    # OpenSSH interpret them as a remote command instead.
    argv[1:1] = ssh_args
    click.echo(shlex.join(argv))
    if print_only:
        return
    completed = subprocess.run(argv, check=False)
    if completed.returncode:
        raise click.exceptions.Exit(completed.returncode)


@devpod.command(name="shell")
@_devpod_resolution_options
def shell_devpod(
    name: Optional[str], id: Optional[str], cluster: Optional[str]
) -> None:
    """Open an interactive shell in your Slurm Dev Pod.

    Select the pod by --name or --id, optionally scoped by --cluster; the
    owning --cluster may also be used alone. The session is tunnelled through
    the workspace API over HTTPS (the same path the dashboard terminal uses),
    so it works wherever `lep` works.
    """
    # Local import keeps websocket-client off the CLI startup path.
    from .ws_shell import ensure_interactive_terminal, run_ws_shell

    _validate_devpod_selector(name, id, cluster)
    ensure_interactive_terminal()
    api = APIClient().slurm
    item = _resolve_devpod_selection(api, name, id, cluster)
    devpod_id = item.metadata.id_
    if not devpod_id:
        raise ValueError("The Slurm Dev Pod response did not contain an ID.")
    console.print(
        f"Opening a shell in Dev Pod [green]{devpod_id}[/]"
        " (type `exit` or press Ctrl-D to leave)..."
    )
    exit_code = run_ws_shell(api.devpod_shell_connection(devpod_id))
    if exit_code:
        raise click.exceptions.Exit(exit_code)


def add_command(cli_group: click.Group) -> None:
    cli_group.add_command(slurm)
