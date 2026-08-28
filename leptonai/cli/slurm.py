"""CLI commands for workspace Slurm resources."""

import json
import shlex
import subprocess
import time
import webbrowser
from datetime import datetime, timezone
from typing import Any, Iterable, List, Optional, Tuple

import click
from rich.table import Table

from ..api.v2.client import APIClient
from ..api.v2.slurm import SlurmAPI
from ..api.v2.types.slurm import (
    LeptonSlurmCluster,
    LeptonSlurmDevPod,
    SlurmJobAttempt,
    WorkspaceSlurmJob,
    WorkspaceSlurmJobList,
)
from .log import _preprocess_time
from .util import click_group, console


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


def _format_time_compact(value: Any) -> str:
    seconds = _epoch_seconds(value)
    if seconds is None:
        return "-"
    try:
        return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M"
        )
    except (OSError, OverflowError, ValueError):
        return str(value)


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


def _print_clusters_table(clusters: Iterable[LeptonSlurmCluster]) -> None:
    table = Table(title="Slurm clusters")
    table.add_column("Name", style="cyan")
    table.add_column("ID")
    table.add_column("State")
    table.add_column("Login nodes")
    table.add_column("Dev Pod")
    table.add_column("Diagnosis")
    for item in clusters:
        status = item.status
        spec = item.spec
        login_nodes = [] if status is None else status.login_node_addresses
        devpods = None if spec is None else spec.dev_pods_config
        table.add_row(
            item.metadata.name or "-",
            item.metadata.id_ or "-",
            (status.state if status else None) or "-",
            ", ".join(login_nodes) or "-",
            "enabled" if devpods and devpods.enabled else "disabled",
            _diagnosis(
                status.reason if status else None, status.error if status else None
            ),
        )
    console.print(table)


def _job_cluster_id(job: WorkspaceSlurmJob) -> str:
    if job.slurm_cluster:
        return job.slurm_cluster.name or job.slurm_cluster.id_ or "-"
    return "-"


def _print_jobs_table(result: WorkspaceSlurmJobList) -> None:
    table = Table(title=f"Slurm jobs ({len(result.jobs)} shown / {result.total} total)")
    table.add_column("Cluster", style="cyan")
    table.add_column("Job / ID")
    table.add_column("State")
    table.add_column("User")
    table.add_column("Partition / QoS")
    table.add_column("CPU / GPU / memory", justify="right")
    table.add_column("Submitted")
    for item in result.jobs:
        state = item.status.job_state or item.status.state or "-"
        job_id = str(item.spec.job_id) if item.spec.job_id is not None else "-"
        table.add_row(
            _job_cluster_id(item),
            f"{item.metadata.name or '-'} / {job_id}",
            state,
            item.metadata.created_by or item.metadata.owner or "-",
            f"{item.status.partition or '-'} / {item.status.qos or '-'}",
            _format_resources(item.spec.cpus, item.spec.gpus, item.spec.memory_mb),
            _format_time_compact(item.metadata.created_at),
        )
    console.print(table)
    if result.failed_clusters:
        console.print("[yellow]Some clusters could not be queried:[/yellow]")
        for cluster_name, error in sorted(result.failed_clusters.items()):
            console.print(f"  {cluster_name}: {error}")


def _print_attempts_table(
    attempts: Iterable[SlurmJobAttempt], *, include_steps: bool
) -> None:
    table = Table(title="Slurm job attempts")
    table.add_column("Attempt / step", style="cyan", min_width=11, no_wrap=True)
    table.add_column("State", min_width=9, no_wrap=True)
    table.add_column("Nodes")
    table.add_column("CPU / GPU / memory", justify="right")
    table.add_column("Started")
    table.add_column("Duration")
    table.add_column("Return")
    for attempt in attempts:
        table.add_row(
            f"attempt {attempt.attempt}",
            attempt.state or "-",
            ", ".join(attempt.nodes) or "-",
            _format_resources(attempt.cpus, attempt.gpus, attempt.memory_mb),
            _format_time_compact(attempt.start_at or attempt.submit_at),
            _format_duration(attempt.start_at, attempt.end_at),
            "-" if attempt.return_code is None else str(attempt.return_code),
        )
        if include_steps:
            for step in attempt.steps:
                table.add_row(
                    f"{attempt.attempt}/{step.id_ or step.name or '-'}",
                    step.state or "-",
                    ", ".join(step.nodes) or "-",
                    _format_resources(step.cpus, step.gpus, step.memory_mb),
                    _format_time_compact(step.start_at or step.submit_at),
                    _format_duration(step.start_at, step.end_at),
                    "-" if step.return_code is None else str(step.return_code),
                )
    console.print(table)


def _print_devpods_table(devpods: Iterable[LeptonSlurmDevPod]) -> None:
    table = Table(title="Slurm Dev Pods")
    table.add_column("ID", style="cyan", overflow="fold")
    table.add_column("Cluster")
    table.add_column("State")
    table.add_column("User")
    table.add_column("CPU req/lim")
    table.add_column("Mem req/lim")
    table.add_column("Image")
    table.add_column("SSH")
    for item in devpods:
        status = item.status
        resources = status.container_resources if status else None
        requests = resources.requests if resources else None
        limits = resources.limits if resources else None
        table.add_row(
            item.metadata.id_ or "-",
            item.spec.slurm_cluster_name,
            (status.state if status else None) or "-",
            (status.username if status else None) or "-",
            f"{(requests.cpu if requests else None) or '-'}/"
            f"{(limits.cpu if limits else None) or '-'}",
            f"{(requests.memory if requests else None) or '-'}/"
            f"{(limits.memory if limits else None) or '-'}",
            (status.image_version if status else None) or "-",
            "ready" if status and status.ssh_command else "-",
        )
    console.print(table)


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


def _open_url(url: str, *, print_only: bool) -> None:
    click.echo(url)
    if print_only:
        return
    if not webbrowser.open(url):
        raise click.ClickException(
            "Could not open a browser. Re-run with --print-only and open the URL "
            "manually."
        )


@click_group()
def slurm():
    """Inspect Slurm clusters/jobs and manage your Slurm Dev Pods."""


@slurm.command(name="dashboard")
@click.option(
    "--view",
    type=click.Choice(("clusters", "jobs"), case_sensitive=False),
    default="clusters",
    show_default=True,
)
@click.option("--jobs", is_flag=True, help="Shortcut for --view jobs.")
@click.option("--print-only", is_flag=True, help="Print the URL without opening it.")
def dashboard(view: str, jobs: bool, print_only: bool) -> None:
    """Open the Slurm dashboard."""
    client = APIClient()
    target_view = "jobs" if jobs else view
    _open_url(client.slurm.dashboard_url(target_view), print_only=print_only)


# ``lep slurm open`` is a concise alias while ``dashboard`` remains explicit.
slurm.add_command(dashboard, name="open")


@slurm.group()
def cluster():
    """Inspect Slurm clusters."""


@cluster.command(name="list")
@click.option("--output", "output_format", "-o", type=OUTPUT_FORMAT, default="table")
def list_clusters(output_format: str) -> None:
    """List Slurm clusters visible in the current workspace."""
    clusters = APIClient().slurm.list_clusters()
    if output_format == "json":
        _print_json(clusters)
    else:
        _print_clusters_table(clusters)


@cluster.command(name="get")
@click.argument("cluster_id")
def get_cluster(cluster_id: str) -> None:
    """Get a Slurm cluster by canonical NAMESPACE/NAME ID."""
    _print_json(APIClient().slurm.get_cluster(cluster_id))


@cluster.command(name="events")
@click.argument("cluster_id")
@click.option("--limit", type=click.IntRange(min=1), default=100, show_default=True)
@click.option("--type", "event_type", help="Filter by cluster event type.")
@click.option("--output", "output_format", "-o", type=OUTPUT_FORMAT, default="table")
def cluster_events(
    cluster_id: str, limit: int, event_type: Optional[str], output_format: str
) -> None:
    """Show lifecycle and administration events for a cluster."""
    events = APIClient().slurm.list_cluster_events(
        cluster_id, limit=limit, event_type=event_type
    )
    if output_format == "json":
        _print_json(events)
        return
    table = Table(title=f"Slurm cluster events: {cluster_id}")
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


@cluster.command(name="open")
@click.argument("cluster_id")
@click.option(
    "--view",
    type=click.Choice(
        (
            "detail",
            "jobs",
            "archived-jobs",
            "events",
            "metrics",
            "logs",
            "devpods",
        ),
        case_sensitive=False,
    ),
    default="detail",
    show_default=True,
)
@click.option("--print-only", is_flag=True, help="Print the URL without opening it.")
def open_cluster(cluster_id: str, view: str, print_only: bool) -> None:
    """Open a cluster view in the dashboard."""
    api = APIClient().slurm
    _open_url(api.dashboard_url(view, cluster_id=cluster_id), print_only=print_only)


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
@click.option("--state", "states", multiple=True, help="Job state; repeatable.")
@click.option("--archived", is_flag=True, help="Show archived jobs only.")
@click.option("--all", "all_jobs", is_flag=True, help="Show live and archived jobs.")
@click.option("--query", "q", "-q", help="Filter by job name substring.")
@click.option("--created-by", multiple=True, help="Creator email; repeatable.")
@click.option("--partition", multiple=True, help="Partition; repeatable.")
@click.option("--qos", multiple=True, help="QoS; repeatable.")
@click.option("--page", type=click.IntRange(min=1))
@click.option("--page-size", type=click.IntRange(min=1, max=500))
@click.option(
    "--sort-by",
    multiple=True,
    type=click.Choice(
        (
            "cluster_name",
            "created_at",
            "job_id",
            "account",
            "priority",
            "cpus",
            "memory_mb",
            "storage_mb",
            "gpus",
            "gpu_memory_mb",
            "node_count",
            "partition",
            "qos",
            "exit_code",
        ),
        case_sensitive=False,
    ),
    help="Sort field; repeatable.",
)
@click.option(
    "--order",
    "sort_orders",
    multiple=True,
    type=click.Choice(("asc", "desc"), case_sensitive=False),
    help="Sort order corresponding to each --sort-by.",
)
@click.option("--output", "output_format", "-o", type=OUTPUT_FORMAT, default="table")
def list_jobs(
    cluster_names: Tuple[str, ...],
    states: Tuple[str, ...],
    archived: bool,
    all_jobs: bool,
    q: Optional[str],
    created_by: Tuple[str, ...],
    partition: Tuple[str, ...],
    qos: Tuple[str, ...],
    page: Optional[int],
    page_size: Optional[int],
    sort_by: Tuple[str, ...],
    sort_orders: Tuple[str, ...],
    output_format: str,
) -> None:
    """List Slurm jobs across one or more clusters."""
    if archived and all_jobs:
        raise click.UsageError("--archived and --all cannot be used together.")
    if sort_orders and len(sort_by) != len(sort_orders):
        raise click.UsageError("Use one --order for each --sort-by value.")
    if sort_by and not sort_orders:
        sort_orders = tuple("desc" for _ in sort_by)

    mode = (
        "archive_only"
        if archived
        else "alive_and_archive" if all_jobs else "alive_only"
    )
    result = APIClient().slurm.list_jobs(
        cluster_names=list(cluster_names) or None,
        job_query_mode=mode,
        q=q,
        status=list(states) or None,
        page=page,
        page_size=page_size,
        created_by=list(created_by) or None,
        partition=list(partition) or None,
        qos=list(qos) or None,
        sort_fields=",".join(sort_by) or None,
        sort_orders=",".join(sort_orders) or None,
    )
    if output_format == "json":
        _print_json(result)
    else:
        _print_jobs_table(result)


@job.command(name="get")
@click.argument("cluster_id")
@click.argument("job_id")
@click.option(
    "--raw-slurm",
    is_flag=True,
    help="Return the untranslated slurmrestd response when supported.",
)
def get_job(cluster_id: str, job_id: str, raw_slurm: bool) -> None:
    """Get JOB_ID from the NAMESPACE/NAME cluster."""
    result = APIClient().slurm.get_job(cluster_id, job_id, slurm_api=raw_slurm)
    _print_json(result)


@job.command(name="attempts")
@click.argument("cluster_id")
@click.argument("job_id")
@click.option("--steps", is_flag=True, help="Include individual Slurm step rows.")
@click.option("--output", "output_format", "-o", type=OUTPUT_FORMAT, default="table")
def job_attempts(cluster_id: str, job_id: str, steps: bool, output_format: str) -> None:
    """Show requeue attempts and steps for a Slurm job."""
    events = APIClient().slurm.get_job_events(cluster_id, job_id)
    if output_format == "json":
        _print_json(events)
    else:
        _print_attempts_table(events.jobs, include_steps=steps)


@job.command(name="logs")
@click.argument("cluster_id")
@click.argument("job_id")
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
    cluster_id: str,
    job_id: str,
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
    """Print or follow stdout/stderr logs for a Slurm job."""
    SlurmAPI.split_cluster_id(cluster_id)
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


@job.command(name="open")
@click.argument("cluster_id")
@click.argument("job_id")
@click.option(
    "--view",
    type=click.Choice(
        ("overview", "attempts", "metrics", "logs"), case_sensitive=False
    ),
    default="overview",
    show_default=True,
)
@click.option("--print-only", is_flag=True, help="Print the URL without opening it.")
def open_job(cluster_id: str, job_id: str, view: str, print_only: bool) -> None:
    """Open a Slurm job view in the dashboard."""
    api = APIClient().slurm
    _open_url(
        api.dashboard_url(view, cluster_id=cluster_id, job_id=job_id),
        print_only=print_only,
    )


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
    devpods = APIClient().slurm.list_devpods(cluster_names=list(cluster_names) or None)
    if output_format == "json":
        _print_json(devpods)
    else:
        _print_devpods_table(devpods)


@devpod.command(name="get")
@click.argument("target")
def get_devpod(target: str) -> None:
    """Get a Dev Pod by ID/name or its NAMESPACE/NAME cluster ID."""
    _print_json(APIClient().slurm.resolve_devpod(target))


@devpod.command(name="create")
@click.argument("cluster_id")
@click.option("--set", "set_name", help="Dev Pod set configured on the cluster.")
@click.option("--cpu", help="CPU request, for example 4 or 500m.")
@click.option("--memory", help="Memory request, for example 16Gi.")
def create_devpod(
    cluster_id: str,
    set_name: Optional[str],
    cpu: Optional[str],
    memory: Optional[str],
) -> None:
    """Create your Dev Pod on a NAMESPACE/NAME Slurm cluster."""
    SlurmAPI.split_cluster_id(cluster_id)
    created = APIClient().slurm.create_devpod(
        cluster_id, set_name=set_name, cpu=cpu, memory=memory
    )
    _print_json(created)


@devpod.command(name="remove")
@click.argument("target")
@click.option("--yes", "assume_yes", "-y", is_flag=True, help="Skip confirmation.")
def remove_devpod(target: str, assume_yes: bool) -> None:
    """Remove a Dev Pod by ID/name or its NAMESPACE/NAME cluster ID."""
    api = APIClient().slurm
    item = api.resolve_devpod(target)
    devpod_id = item.metadata.id_
    if not devpod_id:
        raise ValueError("The Slurm Dev Pod response did not contain an ID.")
    if not assume_yes:
        click.confirm(f"Remove Slurm Dev Pod {devpod_id}?", abort=True)
    api.delete_devpod(devpod_id)
    console.print(f"[green]Removed Slurm Dev Pod {devpod_id}.[/green]")


@devpod.command(name="ssh", context_settings={"ignore_unknown_options": True})
@click.argument("target")
@click.argument("ssh_args", nargs=-1, type=click.UNPROCESSED)
@click.option(
    "--print-only", is_flag=True, help="Print the SSH command without running it."
)
def ssh_devpod(target: str, ssh_args: Tuple[str, ...], print_only: bool) -> None:
    """Connect to a Slurm Dev Pod over its server-provided SSH command.

    Extra SSH options can be passed after ``--``.
    """
    item = APIClient().slurm.resolve_devpod(target)
    command = item.status.ssh_command if item.status else None
    if not command:
        state = item.status.state if item.status else "unknown"
        raise ValueError(
            f"Slurm Dev Pod {item.metadata.id_ or target!r} has no SSH command "
            f"(state: {state})."
        )
    try:
        argv = shlex.split(command)
    except ValueError as error:
        raise ValueError(f"Invalid SSH command returned by the workspace: {error}")
    if not argv or argv[0] != "ssh":
        raise ValueError("The workspace returned an unsupported Dev Pod SSH command.")
    argv.extend(ssh_args)
    click.echo(shlex.join(argv))
    if print_only:
        return
    completed = subprocess.run(argv, check=False)
    if completed.returncode:
        raise click.exceptions.Exit(completed.returncode)


@devpod.command(name="open")
@click.argument("cluster_id")
@click.option("--print-only", is_flag=True, help="Print the URL without opening it.")
def open_devpod(cluster_id: str, print_only: bool) -> None:
    """Open the cluster's Dev Pods dashboard page."""
    api = APIClient().slurm
    _open_url(
        api.dashboard_url("devpods", cluster_id=cluster_id),
        print_only=print_only,
    )


def add_command(cli_group: click.Group) -> None:
    cli_group.add_command(slurm)
