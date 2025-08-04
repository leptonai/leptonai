from typing import List, Optional
import click
from datetime import datetime
import json
import sys

from loguru import logger
from rich.table import Table

from .util import (
    console,
    click_group,
    catch_deprecated_flag,
    check,
    build_dashboard_job_url,
    make_container_ports_from_str_list,
    _validate_queue_priority,
    apply_nodegroup_and_queue_config,
)
from leptonai.api.v1.photon import make_mounts_from_strings, make_env_vars_from_strings
from leptonai.config import BASE_IMAGE, VALID_SHAPES

from leptonai.api.v1.types.common import Metadata, LeptonVisibility
from leptonai.api.v1.types.job import (
    LeptonJob,
    LeptonJobUserSpec,
    LeptonJobState,
)
from leptonai.api.v1.types.deployment import (
    LeptonLog,
)
from leptonai.api.v2.client import APIClient


def _display_jobs_table(jobs: List[LeptonJob], workspace_id: str):
    table = Table(show_header=True, show_lines=True)
    table.add_column("Name / ID")
    table.add_column("Created At")
    table.add_column("State")
    table.add_column("User ID")
    table.add_column("Node Group")
    table.add_column("Workers")
    table.add_column("Shape")

    shape_totals = {}

    for job in jobs:
        ng_str = (
            "\n".join(job.spec.affinity.allowed_dedicated_node_groups).lower()
            if job.spec.affinity and job.spec.affinity.allowed_dedicated_node_groups
            else ""
        )
        status = job.status

        job_url = build_dashboard_job_url(workspace_id, job.metadata.id_)
        name_id_cell = (
            f"[bold #76b900]{job.metadata.name}[/]\n"
            f"[link={job_url}][bright_black]{job.metadata.id_}[/][/link]"
        )
        workers = job.spec.completions or job.spec.parallelism or 1
        shape = job.spec.resource_shape or "-"
        base_cols = [
            name_id_cell,
            (
                datetime.fromtimestamp(job.metadata.created_at / 1000).strftime(
                    "%Y-%m-%d\n%H:%M:%S"
                )
                if job.metadata.created_at
                else "N/A"
            ),
            f"{status.state}",
            job.metadata.owner,
            ng_str,
            str(workers),
            shape,
        ]
        # Count workers towards utilization only if job is actively consuming resources
        if status.state in {
            LeptonJobState.Running,
            LeptonJobState.Restarting,
            LeptonJobState.Deleting,
        }:
            shape_totals[shape] = shape_totals.get(shape, 0) + workers
        table.add_row(*base_cols)

    table.title = "Jobs"
    console.print(table)

    # Print worker count per resource shape
    num_jobs = len(jobs)
    console.print(
        f"[bold]Resource Utilization Summary for above [cyan]{num_jobs}[/]"
        f" job{'s' if num_jobs!=1 else ''} (Running / Restarting / Deleting only):[/]"
    )
    for shape, count in sorted(shape_totals.items()):
        console.print(f"  [bright_black]{shape}[/] : [bold cyan]{count}[/]")
    console.print("\n")


def _filter_jobs(
    jobs: List[LeptonJob],
    state: Optional[List[str]] = None,
    user_patterns: Optional[List[str]] = None,
    name_patterns: Optional[List[str]] = None,
    node_group_patterns: Optional[List[str]] = None,
    exact_users: Optional[List[str]] = None,
    exact_names: Optional[List[str]] = None,
) -> List[LeptonJob]:
    """
    Filter jobs by various criteria.
    Pattern matching (state, user_pattern, name_pattern, node_group_pattern) is case-insensitive and matches the beginning.
    Exact matching (exact_user, exact_name) is case-sensitive and requires full match.

    Args:
        jobs: List of jobs to filter
        state: Optional list of states to filter by (pattern match)
        user_pattern: Optional list of user patterns to filter by (pattern match)
        name_pattern: Optional list of name patterns to filter by (pattern match)
        node_group_pattern: Optional list of node group patterns to filter by (pattern match)
        exact_user: Optional list of exact usernames to filter by (exact match)
        exact_name: Optional list of exact names to filter by (exact match)

    Returns:
        Filtered list of jobs
    """
    # If no filters are specified, return the original list
    if not any([
        state,
        user_patterns,
        name_patterns,
        node_group_patterns,
        exact_users,
        exact_names,
    ]):
        return jobs

    filtered_jobs = []
    for job in jobs:
        # Skip if state filter is specified and job state doesn't match any of the states
        if state and not any(
            job.status.state.lower().startswith(s.lower()) for s in state
        ):
            continue

        # Skip if user pattern filter is specified and job owner doesn't match any of the patterns
        if user_patterns and not any(
            job.metadata.owner.lower().startswith(u.lower()) for u in user_patterns
        ):
            continue

        # Skip if name pattern filter is specified and job name doesn't match any of the patterns
        if name_patterns and not any(
            n.lower() in job.metadata.id_.lower() for n in name_patterns
        ):
            continue

        # Skip if exact user filter is specified and job owner doesn't match exactly
        if exact_users and job.metadata.owner not in exact_users:
            continue

        # Skip if exact name filter is specified and job name doesn't match exactly
        if exact_names and job.metadata.name not in exact_names:
            continue

        # Skip if node group pattern filter is specified and job node group doesn't match any of the patterns
        if node_group_patterns:
            node_groups = (
                job.spec.affinity.allowed_dedicated_node_groups
                if job.spec.affinity
                else None
            )
            if not node_groups or not any(
                pattern.lower() in ng.lower()
                for pattern in node_group_patterns
                for ng in node_groups
            ):
                continue

        filtered_jobs.append(job)

    return filtered_jobs


def _get_newest_job_by_name(job_name: str) -> LeptonJob:
    client = APIClient()
    job_list = client.job.list_all()
    cur_job_list = []
    for job in job_list:
        if job.metadata.name == job_name:
            cur_job_list.append(job)

    if len(cur_job_list) == 0:
        return None

    jobs_sorted_by_created_at = sorted(
        cur_job_list, key=lambda job: job.metadata.created_at
    )

    return jobs_sorted_by_created_at[-1]


@click_group()
def job():
    """
    Manages Lepton Jobs.

    Lepton Jobs are for one-time and one-off tasks that run on one or more machines.
    For example, one can launch a shell script that does a bunch of data processing
    as a job, or a distributed ML training job over multiple, connected machines. See
    the documentation for more details.
    """
    pass


@job.command()
@click.option("--name", "-n", help="Job name", type=str, required=True)
@click.option(
    "--file",
    "-f",
    help=(
        "If specified, load the job spec from the file. Any explicitly passed in arg"
        " will update the spec based on the file."
    ),
    type=str,
)
# Template-based creation options
@click.option(
    "--template",
    "-t",
    help="template ID to render the job specification from.",
    type=str,
)
@click.option(
    "--run",
    help='Command string ("run") to substitute into the template.',
    type=str,
)
# Container specification options
@click.option(
    "--container-image",
    type=str,
    help=(
        "Container image for the job. If not set, default to leptonai.config.BASE_IMAGE"
    ),
    default=None,
)
@click.option(
    "--container-port",
    type=str,
    help=(
        "Ports to expose for the job, in the format"
        " <portnumber>:<protocol(tcp/udp/sctp)>."
    ),
    multiple=True,
)
@click.option(
    "--port",
    "container_port",
    type=str,
    callback=catch_deprecated_flag("port", "container-port"),
    help="Deprecated flag, use --container-port instead.",
    multiple=True,
)
@click.option(
    "--command", type=str, help="Command string to run for the job.", default=None
)

# Resource configuration options
@click.option(
    "--resource-shape",
    "-rs",
    type=str,
    help="Resource shape for the pod. Available types are: '"
    + "', '".join(VALID_SHAPES)
    + "'.",
    default=None,
)
@click.option(
    "--num-workers",
    "-w",
    help=(
        "Number of workers to use for the job. For example, when you do a distributed"
        " training job of 4 replicas, use --num-workers 4."
    ),
    type=int,
    default=None,
)

# Failure handling options
@click.option(
    "--max-failure-retry",
    type=int,
    help="Maximum number of failures to retry per worker.",
    default=None,
)
@click.option(
    "--max-job-failure-retry",
    type=int,
    help="Maximum number of failures to retry per whole job.",
    default=None,
)

# Environment and secrets options
@click.option(
    "--env",
    "-e",
    help="Environment variables to pass to the job, in the format `NAME=VALUE`.",
    multiple=True,
)
@click.option(
    "--secret",
    "-s",
    help=(
        "Secrets to pass to the job, in the format `NAME=SECRET_NAME`. If"
        " secret name is also the environment variable name, you can"
        " omit it and simply pass `SECRET_NAME`."
    ),
    multiple=True,
)
@click.option(
    "--mount",
    help=(
        "Persistent storage to be mounted to the job, in the format"
        " `STORAGE_PATH:MOUNT_PATH` or `STORAGE_PATH:MOUNT_PATH:MOUNT_FROM`."
    ),
    multiple=True,
)
@click.option(
    "--image-pull-secrets",
    type=str,
    help="Secrets to use for pulling images.",
    multiple=True,
)

# Advanced configuration options
@click.option(
    "--intra-job-communication",
    type=bool,
    help=(
        "Enable intra-job communication. If --num-workers is set, this is automatically"
        " enabled."
    ),
    default=None,
)
@click.option(
    "--privileged",
    type=bool,
    is_flag=True,
    help="Run the job in privileged mode.",
    default=None,
)
@click.option(
    "--ttl-seconds-after-finished",
    type=int,
    help=(
        "(advanced feature) limits the lifetime of a job that has finished execution"
        " (either Completed or Failed). If not set, we will have it default to 72"
        " hours. Ref:"
        " https://kubernetes.io/docs/concepts/workloads/controllers/job/#ttl-mechanism-for-finished-jobs"
    ),
    default=259200,
)
@click.option(
    "--log-collection",
    "-lg",
    type=bool,
    help=(
        "Enable or disable log collection (true/false). If not provided, the workspace"
        " setting will be used."
    ),
)

# Node and queue configuration
@click.option(
    "--node-group",
    "-ng",
    "node_groups",
    help=(
        "Node group for the job. If not set, use on-demand resources. You can repeat"
        " this flag multiple times to choose multiple node groups. Multiple node group"
        " option is currently not supported but coming soon for enterprise users. Only"
        " the first node group will be set if you input multiple node groups at this"
        " time."
    ),
    type=str,
    multiple=True,
)
@click.option(
    "--node-id",
    "-ni",
    "node_ids",
    help=(
        "Node for the job. You can repeat this flag multiple times to choose multiple"
        " nodes. Please specify the node group when you are using this option"
    ),
    type=str,
    multiple=True,
)
@click.option(
    "--queue-priority",
    "-qp",
    "queue_priority",
    callback=_validate_queue_priority,
    help=(
        "Set the priority for this job (feature available only for dedicated node"
        " groups).\nCould be one of low-1, low-2, low-3, mid-4, mid-5, mid-6,"
        " high-7, high-8, high-9,Options: 1-9 or keywords: l / low (will be 1), m /"
        " mid (will be 4), h / high (will be 7).\nExamples: -qp 1, -qp 9, -qp low,"
        " -qp mid, -qp high, -qp l, -qp m, -qp h"
    ),
)
@click.option(
    "--can-be-preempted",
    "-cbp",
    is_flag=True,
    default=None,
    help=(
        "Allow this job to be preempted by higher priority jobs (only for dedicated"
        " node groups)."
    ),
)
@click.option(
    "--can-preempt",
    "-cp",
    is_flag=True,
    default=None,
    help=(
        "Allow this job to preempt lower priority jobs (only for dedicated node"
        " groups)."
    ),
)

# Visibility and resource management
@click.option(
    "--visibility",
    type=str,
    help=(
        "Visibility of the job. Can be 'public' or 'private'. If private, the"
        " job will only be viewable by the creator and workspace admin."
    ),
)
@click.option(
    "--shared-memory-size",
    type=int,
    help="Specify the shared memory size for this job, in MiB.",
)
@click.option(
    "--with-reservation",
    type=str,
    help=(
        "Assign the job to a specific reserved compute resource using a reservation ID"
        " (only applicable to dedicated node groups). If not provided, the job will be"
        " scheduled as usual."
    ),
)
@click.option(
    "--allow-burst-to-other-reservation",
    is_flag=True,
    default=False,
    help=(
        "If set, the job can temporarily use free resources from nodes reserved by"
        " other reservations. Be aware that when a new workload bound to those"
        " reservations starts, your job may be evicted."
    ),
)
def create(
    name,
    file,
    template,
    run,
    container_image,
    container_port,
    command,
    resource_shape,
    node_groups,
    num_workers,
    max_failure_retry,
    max_job_failure_retry,
    env,
    secret,
    mount,
    image_pull_secrets,
    intra_job_communication,
    privileged,
    ttl_seconds_after_finished,
    log_collection,
    node_ids,
    queue_priority,
    can_be_preempted,
    can_preempt,
    visibility,
    shared_memory_size,
    with_reservation,
    allow_burst_to_other_reservation,
):
    """
    Creates a job.

    For advanced uses, check https://kubernetes.io/docs/concepts/workloads/controllers/job/.
    """
    # Initialize API client
    client = APIClient()

    # Load job specification from template or file
    if run is not None and template is None:
        console.print("[red]Error[/]: --run can only be used together with --template.")
        sys.exit(1)

    if template:
        try:
            payload = {"run": run} if run else {}
            rendered_job = client.template.render(template, payload)
            job_spec = rendered_job.spec
        except Exception as e:
            console.print(f"[red]Failed to render template[/]: {e}")
            sys.exit(1)
    elif file:
        try:
            with open(file, "r") as f:
                content = f.read()
                job_spec = LeptonJobUserSpec.parse_raw(content)
        except Exception as e:
            console.print(f"Cannot load job spec from file [red]{file}[/]: {e}")
            return
    else:
        job_spec = LeptonJobUserSpec()

    # Apply shared node group / queue / reservation config
    try:
        apply_nodegroup_and_queue_config(
            spec=job_spec,
            node_groups=node_groups,
            node_ids=node_ids,
            queue_priority=queue_priority,
            can_be_preempted=can_be_preempted,
            can_preempt=can_preempt,
            with_reservation=with_reservation,
            allow_burst=allow_burst_to_other_reservation,
        )
    except ValueError as e:
        console.print(f"[red]{e}[/]")
        sys.exit(1)

    # Set resource shape
    if resource_shape:
        job_spec.resource_shape = resource_shape
    elif not job_spec.resource_shape:
        available_types = "\n      ".join(VALID_SHAPES)
        console.print(
            "[red]Error: Missing option '--resource-shape'.[/] "
            f"Available types are:\n      {available_types} \n"
        )
        sys.exit(1)

    # Configure worker settings
    if num_workers:
        job_spec.completions = num_workers
        job_spec.parallelism = num_workers
        job_spec.intra_job_communication = True
    elif intra_job_communication:
        job_spec.intra_job_communication = intra_job_communication

    # Set failure retry limits
    if max_failure_retry:
        job_spec.max_failure_retry = max_failure_retry
    if max_job_failure_retry:
        job_spec.max_job_failure_retry = max_job_failure_retry

    # Configure container settings
    if command:
        # For CLI passed in command, we will prepend it with /bin/bash -c
        command = ["/bin/bash", "-c", command]
        job_spec.container.command = command

    # Set container image
    if container_image:
        job_spec.container.image = container_image
    elif not job_spec.container.image:
        job_spec.container.image = BASE_IMAGE

    # Configure container ports
    if container_port:
        try:
            parsed_ports = make_container_ports_from_str_list(
                container_port, strategy_free=True
            )
        except ValueError as e:
            console.print(f"[red]Error[/]: {e}")
            sys.exit(1)

        job_spec.container.ports = parsed_ports

    # Set environment variables and secrets
    if env or secret:
        job_spec.envs = make_env_vars_from_strings(env, secret)  # type: ignore

    # Configure mounts
    if mount:
        job_spec.mounts = make_mounts_from_strings(mount)  # type: ignore

    # Set image pull secrets
    if image_pull_secrets:
        job_spec.image_pull_secrets = image_pull_secrets

    # Configure advanced settings
    if privileged:
        job_spec.privileged = privileged
    if ttl_seconds_after_finished:
        job_spec.ttl_seconds_after_finished = ttl_seconds_after_finished
    if log_collection is not None:
        job_spec.log = LeptonLog(enable_collection=log_collection)
    if shared_memory_size is not None:
        job_spec.shared_memory_size = shared_memory_size

    # Create job with metadata
    job = LeptonJob(
        spec=job_spec,
        metadata=Metadata(
            id=name,
            visibility=LeptonVisibility(visibility) if visibility else None,
        ),
    )

    # Log job specification for debugging
    logger.trace(json.dumps(job.model_dump(), indent=2))
    # Create job and display success message
    created_job = client.job.create(job)
    new_job_id = created_job.metadata.id_
    console.print(
        f"🎉 [green]Job Created Successfully![/]\nName: [blue]{name}[/]\nID:"
        f" [cyan]{new_job_id}[/]"
    )


@job.command(name="list")
@click.option(
    "--state",
    "-s",
    help=(
        "Filter jobs by state. Case-insensitive and matches the beginning of the state"
        " name. Available states: Starting, Running, Failed, Completed, Stopped,"
        " Stopping, Deleting, Deleted, Restarting, Archived, Queueing, Awaiting,"
        " PendingRetry. Example: 'run' will match 'Running'. Can specify multiple"
        " states."
    ),
    type=str,
    required=False,
    multiple=True,
)
@click.option(
    "--user",
    "-u",
    help=(
        "Filter jobs by user. Case-insensitive and matches the beginning of the"
        " username. Can specify multiple users. Example: 'alice' will match 'alice123'"
    ),
    type=str,
    required=False,
    multiple=True,
)
@click.option(
    "--name-or-id",
    "-n",
    help=(
        "Filter jobs by name or id. Case-insensitive and matches any part of the name"
        " or id. Can specify multiple names or ids. Example: 'train' will match"
        " 'training-job-123'"
    ),
    type=str,
    required=False,
    multiple=True,
)
@click.option(
    "--node-group",
    "-ng",
    help=(
        "Filter jobs by node group. Case-insensitive and matches any part of the node"
        " group name."
    ),
    type=str,
    required=False,
    multiple=True,
)
def list_command(state, user, name_or_id, node_group):
    """
    Lists all jobs in the current workspace.

    You can filter jobs by:
    - State: Case-insensitive prefix match (e.g., 'run' matches 'Running')
    - User: Case-insensitive prefix match (e.g., 'alice' matches 'alice123')
    - Name/ID: Case-insensitive substring match (e.g., 'train' matches 'training-job-123')
    - Node Group: Case-insensitive substring match

    Multiple filters can be combined. For example:
    lep job list -s queue -u alice -n train -ng h100
    """
    client = APIClient()
    jobs = client.job.list_all()
    logger.trace(f"Jobs: {jobs}")

    job_filtered = _filter_jobs(
        jobs,
        state,
        user_patterns=user,
        name_patterns=name_or_id,
        node_group_patterns=node_group,
    )

    _display_jobs_table(job_filtered, client.get_workspace_id())


@job.command()
@click.option(
    "--state",
    "-s",
    help=(
        "Filter jobs by state. Case-insensitive and matches the beginning of the state"
        " name. Available states: Starting, Running, Failed, Completed, Stopped,"
        " Stopping, Deleting, Deleted, Restarting, Archived, Queueing, Awaiting,"
        " PendingRetry. Example: 'run' will match 'Running'. Can specify multiple"
        " states."
    ),
    type=str,
    required=False,
    multiple=True,
)
@click.option(
    "--user",
    "-u",
    help=(
        "Filter jobs by exact user ID match. Case-sensitive. "
        "Can specify multiple users. For safety, this is an exact match. "
        "This option is required to prevent accidental operations on other users' jobs."
    ),
    type=str,
    required=True,
    multiple=True,
)
@click.option(
    "--name",
    "-n",
    help=(
        "Filter jobs by exact name match. Case-sensitive. "
        "Can specify multiple names. For safety, this is an exact match."
    ),
    type=str,
    required=False,
    multiple=True,
)
@click.option(
    "--node-group",
    "-ng",
    help=(
        "Filter jobs by node group. Case-insensitive and matches any part of the node"
        " group name."
    ),
    type=str,
    required=False,
    multiple=True,
)
def remove_all(state, user, name, node_group):
    """
    Removes all jobs matching the specified filters. At least one filter must be provided.
    For safety, name and user filters require exact matches. State filter remains flexible.
    The --user option is required to prevent accidental operations on other users' jobs.
    """
    if not state and not user and not name and not node_group:
        console.print("[red]Error[/]: You must provide at least one filter.")
        sys.exit(1)

    client = APIClient()
    jobs = client.job.list_all()
    job_filtered = _filter_jobs(
        jobs, state, node_group_patterns=node_group, exact_users=user, exact_names=name
    )

    if len(job_filtered) == 0:
        console.print(
            "[yellow]No jobs matched your filters.[/]\n"
            "[cyan]Note[/]: remove-all requires an exact match for '--user' "
            "(User ID shown in `lep job list`). Please verify your input."
        )
        sys.exit(0)

    _display_jobs_table(job_filtered, client.get_workspace_id())

    user_set = set(job.metadata.owner for job in job_filtered)

    console.print(f"Total [red]{len(job_filtered)}[/] jobs to delete.")
    console.print(
        f"These jobs belong to [green]{len(user_set)}[/] user(s):"
        f" [green]{', '.join(user_set)}[/]"
    )

    console.print("To confirm deletion, please enter the number of jobs to delete:")
    try:
        confirm_count = int(click.prompt("Number of jobs to delete", type=int))
        if confirm_count != len(job_filtered):
            console.print(
                f"[red]Error[/]: Number mismatch. Expected {len(job_filtered)} jobs."
            )
            sys.exit(1)
    except ValueError:
        console.print("[red]Error[/]: Please enter a valid number.")
        sys.exit(1)

    for job in job_filtered:
        client.job.delete(job.metadata.id_)
        console.print(f"Job [green]{job.metadata.id_}[/] deleted successfully.")


@job.command()
@click.option(
    "--state",
    "-s",
    help=(
        "Filter jobs by state. Case-insensitive and matches the beginning of the state"
        " name. Available states: Starting, Running, Failed, Completed, Stopped,"
        " Stopping, Deleting, Deleted, Restarting, Archived, Queueing, Awaiting,"
        " PendingRetry. Example: 'run' will match 'Running'. Can specify multiple"
        " states."
    ),
    type=str,
    required=False,
    multiple=True,
)
@click.option(
    "--user",
    "-u",
    help=(
        "Filter jobs by exact user ID match. Case-sensitive. "
        "Can specify multiple users. For safety, this is an exact match. "
        "This option is required to prevent accidental operations on other users' jobs."
    ),
    type=str,
    required=True,
    multiple=True,
)
@click.option(
    "--name",
    "-n",
    help=(
        "Filter jobs by exact name match. Case-sensitive. "
        "Can specify multiple names. For safety, this is an exact match."
    ),
    type=str,
    required=False,
    multiple=True,
)
@click.option(
    "--node-group",
    "-ng",
    help=(
        "Filter jobs by node group. Case-insensitive and matches any part of the node"
        " group name."
    ),
    type=str,
    required=False,
    multiple=True,
)
def stop_all(state, user, name, node_group):
    """
    Stop all jobs matching the specified filters. At least one filter must be provided.
    For safety, name and user filters require exact matches. State filter remains flexible.
    The --user option is required to prevent accidental operations on other users' jobs.
    """
    if not state and not user and not name and not node_group:
        console.print("[red]Error[/]: You must provide at least one filter.")
        sys.exit(1)

    client = APIClient()
    jobs = client.job.list_all()
    job_filtered = _filter_jobs(
        jobs, state, node_group_patterns=node_group, exact_users=user, exact_names=name
    )

    if len(job_filtered) == 0:
        console.print(
            "[yellow]No jobs matched your filters.[/]\n"
            "[cyan]Note[/]: stop-all requires an exact match for '--user' "
            "(User ID shown in `lep job list`). Please verify your input."
        )
        sys.exit(0)

    _display_jobs_table(job_filtered, client.get_workspace_id())

    user_set = set(job.metadata.owner for job in job_filtered)

    console.print(f"Total [red]{len(job_filtered)}[/] jobs to stop.")
    console.print(
        f"These jobs belong to [green]{len(user_set)}[/] user(s):"
        f" [green]{', '.join(user_set)}[/]"
    )

    console.print("To confirm stop, please enter the number of jobs to stop:")
    try:
        confirm_count = int(click.prompt("Number of jobs to stop", type=int))
        if confirm_count != len(job_filtered):
            console.print(
                f"[red]Error[/]: Number mismatch. Expected {len(job_filtered)} jobs."
            )
            sys.exit(1)
    except ValueError:
        console.print("[red]Error[/]: Please enter a valid number.")
        sys.exit(1)

    for job in job_filtered:
        client.job.update(job.metadata.id_, spec={"spec": {"stopped": True}})
        console.print(f"Job [green]{job.metadata.id_}[/] stopped successfully.")


@job.command()
@click.option("--name", "-n", help="Job name", type=str, required=False)
@click.option("--id", "-i", help="Job id", type=str, required=False)
@click.option(
    "--path",
    "-p",
    type=click.Path(
        exists=False,
        file_okay=True,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
    help=(
        "Optional local path to save the job spec JSON. Directory or full filename"
        " accepted.\nIf a directory is provided, the file will be saved as"
        " job-spec-<job_id>.json so it can be reused with `lep job create --file`."
    ),
    required=False,
)
def get(name, id, path):
    """
    Gets detailed information about jobs.

    You can search by either name or id:
    - If searching by name, returns all jobs with that exact name
    - If searching by id, returns the specific job with that id

    Args:
        name: Job name to search for (exact match)
        id: Job id to search for (exact match)
        path: Optional path (file or directory) to save the job spec JSON
    """
    if not name and not id:
        raise click.UsageError("You must provide either --name or --id.")
    if name and id:
        raise click.UsageError(
            "You cannot provide both --name and --id. Please specify only one."
        )

    client = APIClient()
    target_jobs = []

    if id:
        job = client.job.get(id)
        target_jobs.append(job)

    if name:
        jobs = client.job.list_all()
        for job in jobs:
            if job.metadata.name == name:
                target_jobs.append(job)

    if len(target_jobs) == 0:
        search_type = "Name" if name else "ID"
        console.print(f"No job found for [red]{search_type}: {name or id}[/].")
        sys.exit(1)

    console.print(f"Job details for [green]{name or id}[/]:")
    for job in target_jobs:
        console.print(json.dumps(client.job.safe_json(job), indent=2))
        console.print("--------------------------\n")

    # Save spec to file if requested.
    if path:
        if len(target_jobs) != 1:
            console.print(
                "[red]Error[/]: --path option requires exactly one matched job. "
                "Please specify a unique --id or --name."
            )
            sys.exit(1)

        import os

        job = target_jobs[0]
        job_spec_json = job.spec.model_dump_json(indent=2)

        # Determine final save path
        save_path = path

        if os.path.isdir(path) or path.endswith(os.sep):
            # Path is a directory (existing or intended). Ensure it exists.
            os.makedirs(path, exist_ok=True)
            save_path = os.path.join(path, f"job-spec-{job.metadata.id_}.json")
        else:
            # Ensure parent dir exists
            parent_dir = os.path.dirname(save_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

        try:
            with open(save_path, "w") as f:
                f.write(job_spec_json)
            console.print(f"Job spec saved to [green]{save_path}[/].")
        except Exception as e:
            console.print(f"[red]Failed to save job spec: {e}[/]")
            sys.exit(1)


@job.command()
@click.option(
    "--id", "-i", help="The ID of the job to remove.", type=str, required=False
)
@click.option(
    "--name",
    "-n",
    help=(
        "The name of the job to remove. If multiple jobs share the same name, all of"
        " them will be removed."
    ),
    required=False,
)
def remove(id, name):
    """
    Removes a single job.

    You can remove a job by either name or id:
    - If removing by name, only the newest job with that exact name will be removed
    - If removing by id, the specific job with that id will be removed

    For removing multiple jobs with the same name, use 'lep job remove-all' instead.

    Args:
        id: Job id to remove (exact match)
        name: Job name to remove (exact match, removes only the newest matching job)
    """
    if not name and not id:
        raise click.UsageError("You must provide either --name or --id.")
    if name and id:
        raise click.UsageError(
            "You cannot provide both --name and --id. Please specify only one."
        )

    client = APIClient()

    target_job_ids = []
    if id:
        target_job_ids.append(id)

    if name:
        job = _get_newest_job_by_name(name)
        if job:
            target_job_ids.append(job.metadata.id_)
        else:
            console.print(f"No job found with name [red]{name}[/].")
            sys.exit(1)

    for job_id in target_job_ids:
        client.job.delete(job_id)
        console.print(f"Job [green]{job_id}[/] deleted successfully.")


@job.command()
@click.option("--id", "-i", help="The job id to get events.", required=True)
def clone(id):
    """
    Creates a copy of an existing job by its ID.

    The cloned job will:
    - Have the same configuration as the original job
    - Have a new name with '-clone' suffix

    Args:
        id: ID of the job to clone
    """
    client = APIClient()
    job = client.job.get(id)
    job_spec = job.spec

    visibility = job.metadata.visibility
    name = job.metadata.name[:26] + "-clone"

    job = LeptonJob(
        spec=job_spec,
        metadata=Metadata(
            id=name,
            visibility=LeptonVisibility(visibility) if visibility else None,
        ),
    )

    new_job = client.job.create(job)
    console.print(f"Job [green]{new_job.metadata.id_}[/] cloned successfully.")


@job.command()
@click.option("--id", "-i", help="The job id to get log.", required=True)
@click.option("--replica", "-r", help="The replica name to get log.", default=None)
def log(id, replica):
    """
    Gets the log of a job. If `replica` is not specified, the first replica
    is selected. Otherwise, the log of the specified replica is shown. To get the
    list of replicas, use `lep job replicas`.
    """
    client = APIClient()

    if not replica:
        # obtain replica information, and then select the first one.
        console.print(
            f"Replica name not specified for [yellow]{id}[/]. Selecting the first"
            " replica."
        )

        replicas = client.job.get_replicas(id)
        check(len(replicas) > 0, f"No replicas found for [red]{id}[/].")
        replica = replicas[0].metadata.id_
        console.print(f"Selected replica [green]{replica}[/].")
    else:
        console.print(f"Showing log for replica [green]{replica}[/].")
    stream_or_err = client.job.get_log(id_or_job=id, replica=replica)
    # Print the log as a continuous stream until the user presses Ctrl-C.
    try:
        for chunk in stream_or_err:
            console.print(chunk, end="")
    except KeyboardInterrupt:
        console.print("Disconnected.")
    except Exception:
        console.print("Connection stopped.")
        return
    else:
        console.print(
            "End of log. It seems that the job has not started, or already finished."
        )


@job.command()
@click.option("--id", "-i", help="The job id to get replicas.", required=True)
def replicas(id):
    """
    Prints the replicas id of a job.
    """
    client = APIClient()

    replicas = client.job.get_replicas(id)

    table = Table(show_header=True, show_lines=False)
    table.add_column("Job Name")
    table.add_column("Replica ID")
    table.add_column("Node ID")

    for replica in replicas:
        node_id = None
        if replica.status and replica.status.node:
            node_id = replica.status.node.id_
        table.add_row(id, replica.metadata.id_, node_id)
    console.print(table)


@job.command()
@click.option("--id", "-i", help="The job id to get replicas.", required=True)
def nodes(id):
    """
    Prints the nodes id of a job.
    """
    client = APIClient()

    replicas = client.job.get_replicas(id)
    node_list = []
    for replica in replicas:
        if replica.status and replica.status.node:
            node_list.append(replica.status.node.id_)
    node_list = sorted(node_list)

    console.print("\n[bold blue]Job Nodes:[/] \n")
    console.print("[green]" + json.dumps(node_list, indent=2) + "[/]\n")


@job.command()
@click.option("--id", "-i", help="The job id to stop.", required=True)
def stop(id):
    """
    Stops a job by its ID.

    Args:
        id: ID of the job to stop
    """
    client = APIClient()
    cur_job = client.job.get(id)
    if cur_job.spec.stopped is True:
        console.print(
            f"[yellow]⚠ Job [bold]{id}[/] is already stopped. No action taken.[/]"
        )
        sys.exit(0)
    client.job.update(id, spec={"spec": {"stopped": True}})

    console.print(f"Job [green]{id}[/] stopped successfully.")


@job.command()
@click.option("--id", "-i", help="The job id to start.", required=True)
def start(id):
    """
    Starts a job by its ID.

    Args:
        id: ID of the job to start
    """
    client = APIClient()
    cur_job = client.job.get(id)
    if (
        cur_job.spec.stopped is False
        or cur_job.status.state is not LeptonJobState.Stopped
    ):
        console.print(
            f"[yellow]⚠ Job [bold]{id}[/] is {cur_job.status.state}. No action"
            " taken.[/]"
        )
        sys.exit(0)
    client.job.update(id, spec={"spec": {"stopped": False}})

    console.print(f"Job [green]{id}[/] started successfully.")


@job.command()
@click.option("--id", "-i", help="The job id to get events.", required=True)
def events(id, replica=None):
    """
    Prints the events of a job by its ID.

    Args:
        id: ID of the job to get events
    """
    client = APIClient()

    events = client.job.get_events(id)

    table = Table(title="Job Events", show_header=True, show_lines=False)
    table.add_column("Job Name")
    table.add_column("Type")
    table.add_column("Reason")
    table.add_column("Regarding")
    table.add_column("Count")
    table.add_column("Last Observed Time")
    for event in events:
        date_string = event.last_observed_time.strftime("%Y-%m-%d %H:%M:%S")
        table.add_row(
            id,
            event.type_,
            event.reason,
            str(event.regarding),
            str(event.count),
            date_string,
        )
    console.print(table)


def add_command(cli_group):
    cli_group.add_command(job)
