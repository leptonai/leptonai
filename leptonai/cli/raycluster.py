import json
import shlex
from datetime import datetime
import sys
import warnings
import urllib3
import yaml
import asyncio
import textwrap

import click
from ray.job_submission import JobSubmissionClient, JobStatus
from rich.table import Table
from rich.pretty import Pretty

from .util import (
    console,
    click_group,
    apply_nodegroup_and_queue_config,
    resolve_save_path,
    PathResolutionError,
)
from ..api.v2.client import APIClient
from ..api.v1.types.common import LeptonVisibility, Metadata, LeptonUserSecurityContext
from ..api.v1.types.raycluster import (
    LeptonRayCluster,
    LeptonRayClusterUserSpec,
    RayHeadGroupSpec,
    RayWorkerGroupSpec,
    RayAutoscaler,
    RayClusterCommonGroupSpec,
)
from ..api.v1.photon import make_mounts_from_strings, make_env_vars_from_strings
from ..api.v1.types.deployment import LeptonContainer
from ..api.v1.types.job import LeptonJobSegmentConfig

DEFAULT_RAY_IMAGE = "ray:2.49.2-py312-gpu"
DEFAULT_RAY_IMAGES = {
    # unprefixed tags
    "2.46.0": "2.46.0",
    "2.46.0-py310-cpu": "2.46.0",
    "2.46.0-py311-cpu": "2.46.0",
    "2.46.0-py312-cpu": "2.46.0",
    "2.46.0-py310-gpu": "2.46.0",
    "2.46.0-py311-gpu": "2.46.0",
    "2.46.0-py312-gpu": "2.46.0",
    "2.47.0": "2.47.0",
    "2.47.0-py310-cpu": "2.47.0",
    "2.47.0-py311-cpu": "2.47.0",
    "2.47.0-py312-cpu": "2.47.0",
    "2.47.0-py310-gpu": "2.47.0",
    "2.47.0-py311-gpu": "2.47.0",
    "2.47.0-py312-gpu": "2.47.0",
    "2.48.0": "2.48.0",
    "2.48.0-py310-cpu": "2.48.0",
    "2.48.0-py311-cpu": "2.48.0",
    "2.48.0-py312-cpu": "2.48.0",
    "2.48.0-py310-gpu": "2.48.0",
    "2.48.0-py311-gpu": "2.48.0",
    "2.48.0-py312-gpu": "2.48.0",
    "2.49.0": "2.49.0",
    "2.49.0-py310-cpu": "2.49.0",
    "2.49.0-py311-cpu": "2.49.0",
    "2.49.0-py312-cpu": "2.49.0",
    "2.49.0-py310-gpu": "2.49.0",
    "2.49.0-py311-gpu": "2.49.0",
    "2.49.0-py312-gpu": "2.49.0",
    "2.49.1": "2.49.1",
    "2.49.1-py310-cpu": "2.49.1",
    "2.49.1-py311-cpu": "2.49.1",
    "2.49.1-py312-cpu": "2.49.1",
    "2.49.1-py310-gpu": "2.49.1",
    "2.49.1-py311-gpu": "2.49.1",
    "2.49.1-py312-gpu": "2.49.1",
    "2.49.2": "2.49.2",
    "2.49.2-py310-cpu": "2.49.2",
    "2.49.2-py311-cpu": "2.49.2",
    "2.49.2-py312-cpu": "2.49.2",
    "2.49.2-py310-gpu": "2.49.2",
    "2.49.2-py311-gpu": "2.49.2",
    "2.49.2-py312-gpu": "2.49.2",
    # prefixed official images
    "ray:2.46.0": "2.46.0",
    "ray:2.46.0-py310-cpu": "2.46.0",
    "ray:2.46.0-py311-cpu": "2.46.0",
    "ray:2.46.0-py312-cpu": "2.46.0",
    "ray:2.46.0-py310-gpu": "2.46.0",
    "ray:2.46.0-py311-gpu": "2.46.0",
    "ray:2.46.0-py312-gpu": "2.46.0",
    "ray:2.47.0": "2.47.0",
    "ray:2.47.0-py310-cpu": "2.47.0",
    "ray:2.47.0-py311-cpu": "2.47.0",
    "ray:2.47.0-py312-cpu": "2.47.0",
    "ray:2.47.0-py310-gpu": "2.47.0",
    "ray:2.47.0-py311-gpu": "2.47.0",
    "ray:2.47.0-py312-gpu": "2.47.0",
    "ray:2.48.0": "2.48.0",
    "ray:2.48.0-py310-cpu": "2.48.0",
    "ray:2.48.0-py311-cpu": "2.48.0",
    "ray:2.48.0-py312-cpu": "2.48.0",
    "ray:2.48.0-py310-gpu": "2.48.0",
    "ray:2.48.0-py311-gpu": "2.48.0",
    "ray:2.48.0-py312-gpu": "2.48.0",
    "ray:2.49.0": "2.49.0",
    "ray:2.49.0-py310-cpu": "2.49.0",
    "ray:2.49.0-py311-cpu": "2.49.0",
    "ray:2.49.0-py312-cpu": "2.49.0",
    "ray:2.49.0-py310-gpu": "2.49.0",
    "ray:2.49.0-py311-gpu": "2.49.0",
    "ray:2.49.0-py312-gpu": "2.49.0",
    "ray:2.49.1": "2.49.1",
    "ray:2.49.1-py310-cpu": "2.49.1",
    "ray:2.49.1-py311-cpu": "2.49.1",
    "ray:2.49.1-py312-cpu": "2.49.1",
    "ray:2.49.1-py310-gpu": "2.49.1",
    "ray:2.49.1-py311-gpu": "2.49.1",
    "ray:2.49.1-py312-gpu": "2.49.1",
    "ray:2.49.2": "2.49.2",
    "ray:2.49.2-py310-cpu": "2.49.2",
    "ray:2.49.2-py311-cpu": "2.49.2",
    "ray:2.49.2-py312-cpu": "2.49.2",
    "ray:2.49.2-py310-gpu": "2.49.2",
    "ray:2.49.2-py311-gpu": "2.49.2",
    "ray:2.49.2-py312-gpu": "2.49.2",
}


class WorkerGroupCommand(click.Command):
    """
    A custom click.Command that pre-parses repeatable worker-group parameter blocks.
    It recognizes '-wg/--worker-group' as a group marker and consumes the per-group
    options that follow it until the next marker, assembling a list of dictionaries.
    The parsed list is injected into ctx.params['worker_groups'] and all group-related
    tokens are removed from the argument list before delegating to Click's parser.
    """

    _WG_MARKERS = ("-wg", "--worker-group")
    _GROUP_FLAGS = {
        "--group-name": "group_name",
        "--image": "image",
        "--command": "command",
        "--resource-shape": "resource_shape",
        "--shared-memory-size": "shared_memory_size",
        "--min-replicas": "min_replicas",
        "--max-replicas": "max_replicas",
        "--segment-count": "segment_count",
        "--node-group": "node_group",
        "--allowed-nodes": "allowed_nodes",
        "--reservation": "reservation",
        "--allow-burst": "allow_burst",
        "--privileged": "privileged",
        "--env": "env",
        "-e": "env",
        "--secret": "secret",
        "-s": "secret",
        "--mount": "mount",
    }
    _LIST_FIELDS = {"env", "secret", "mount"}

    def parse_args(self, ctx, args):
        groups = []
        current = None
        remaining = []

        def ensure_current():
            nonlocal current
            if current is None:
                current = {
                    "group_name": None,
                    "image": None,
                    "command": None,
                    "resource_shape": None,
                    "shared_memory_size": None,
                    "min_replicas": None,
                    "max_replicas": None,
                    "segment_count": None,
                    "node_group": None,
                    "allowed_nodes": None,
                    "reservation": None,
                    "allow_burst": None,
                    "env": [],
                    "secret": [],
                    "mount": [],
                }

        i = 0
        n = len(args)
        while i < n:
            tok = args[i]
            if tok in self._WG_MARKERS:
                # close previous
                if current is not None:
                    groups.append(current)
                current = None
                ensure_current()
                i += 1
                continue

            # Handle --opt=value
            flag, value = None, None
            if tok.startswith("--"):
                if "=" in tok:
                    flag, value = tok.split("=", 1)
                else:
                    flag = tok
            elif tok in ("-e", "-s"):
                flag = tok

            if flag in self._GROUP_FLAGS:
                if current is None:
                    raise click.UsageError(
                        f'"{flag}" must follow a "-wg/--worker-group" marker.'
                    )
                # If value not provided inline, consume next token
                if value is None:
                    # NOTE: values may legitimately start with '-' (e.g. negative numbers),
                    # so only treat the next token as "missing" when it is clearly another
                    # flag/marker we understand.
                    if i + 1 >= n:
                        raise click.UsageError(f'"{flag}" requires a value.')
                    nxt = args[i + 1]
                    if (
                        nxt in self._WG_MARKERS
                        or nxt in self._GROUP_FLAGS
                        or nxt.startswith("--")
                    ):
                        raise click.UsageError(f'"{flag}" requires a value.')
                    value = args[i + 1]
                    i += 1

                key = self._GROUP_FLAGS[flag]
                if key in self._LIST_FIELDS:
                    # accumulate, support comma-separated lists, split later
                    getattr_list = current.get(key)
                    if getattr_list is None:
                        getattr_list = []
                        current[key] = getattr_list
                    getattr_list.append(value)
                else:
                    current[key] = value
                i += 1
                continue

            # Non-group option; preserve for Click
            remaining.append(tok)
            i += 1

        if current is not None:
            groups.append(current)

        ctx.params["worker_groups"] = groups
        return super().parse_args(ctx, remaining)

    def get_help(self, ctx):
        base_help = super().get_help(ctx)
        # Only augment help for the 'create' subcommand; 'update' already documents its flags.
        if getattr(self, "name", None) != "create":
            return base_help
        group_help = textwrap.dedent("""
            Worker group blocks (-wg/--worker-group)
              Define one or more worker groups by repeating a -wg/--worker-group marker,
              followed by any of these per-group flags. Example:
                lep raycluster create -n myrc -wg --group-name g1 --resource-shape A100:1 --node-group ng-a \\
                  --min-replicas 2 --env FOO=bar -wg --group-name g2 --resource-shape A100:2 --node-group ng-b

              Per-group flags:
                --group-name TEXT
                    Logical name for this worker group.
                --image TEXT
                    Container image for this group's workers.
                --command TEXT
                    Container command (as a single string; shlex-split).
                --resource-shape TEXT
                    REQUIRED. Resource shape identifier for nodes (e.g., GPU/CPU shape).
                --shared-memory-size INTEGER
                    Size of shared memory in MiB allocated to the container.
                --min-replicas INTEGER
                    Minimum number of replicas (default: 1).
                --max-replicas INTEGER
                    Only when autoscaler is enabled; must be greater than --min-replicas.
                --segment-count INTEGER
                    Only when autoscaler is disabled; must be positive and evenly divide --min-replicas.
                --node-group TEXT
                    REQUIRED. Dedicated node group (affinity) for this worker group.
                --allowed-nodes TEXT
                    Comma-separated node names within the chosen node group.
                --reservation TEXT
                    Reservation ID to place the group onto.
                --allow-burst BOOL
                    Allow bursting to other reservations when available (true/false).
                --privileged BOOL
                    Run containers in privileged mode (true/false).
                --env, -e NAME=VALUE
                    Repeatable or comma-separated. Environment variables to set.
                --secret, -s NAME=SECRET_NAME
                    Repeatable or comma-separated. Inject secret as env var NAME from secret SECRET_NAME.
                --mount STORAGE_PATH:MOUNT_PATH:MOUNT_FROM
                    Repeatable or comma-separated. Persistent storage mount specification.
            """).rstrip()
        return f"{base_help}\n\n{group_help}"


def _validate_resource_shape_nonempty(resource_shape: str | None, label: str) -> None:
    if resource_shape is None or resource_shape == "":
        console.print(f"[red]{label} resource shape is required.[/]")
        sys.exit(1)


def _validate_shared_memory_non_negative(
    shared_memory_size: int | None, label: str
) -> None:
    if shared_memory_size is not None and shared_memory_size < 0:
        console.print(f"[red]{label} shared memory size must be non-negative.[/]")
        sys.exit(1)


def _apply_affinity_and_reservation(
    spec,
    node_groups: list[str] | None,
    reservation: str | None,
    allow_burst: bool | None,
) -> None:
    apply_nodegroup_and_queue_config(
        spec=spec,
        node_groups=node_groups,
        node_ids=None,
        queue_priority=None,
        can_be_preempted=None,
        can_preempt=None,
        with_reservation=reservation,
        allow_burst=allow_burst,
    )


def _validate_exactly_one_node_group(spec, label: str) -> None:
    if (
        not getattr(spec, "affinity", None)
        or not getattr(spec.affinity, "allowed_dedicated_node_groups", None)
        or len(spec.affinity.allowed_dedicated_node_groups) != 1
    ):
        console.print(
            f"[red]{label} node group is required and must be exactly one.[/]"
        )
        sys.exit(1)


def _set_allowed_nodes_in_affinity(spec, allowed_nodes_csv: str | None) -> None:
    if not allowed_nodes_csv:
        return
    nodes = [x.strip() for x in allowed_nodes_csv.split(",") if x.strip()]
    if nodes:
        # ensure affinity exists after node group application
        if not getattr(spec, "affinity", None):
            return
        spec.affinity.allowed_nodes_in_node_group = nodes


def _build_group_spec(
    *,
    spec: RayClusterCommonGroupSpec,
    label: str,
    resource_shape: str | None,
    shared_memory_size: int | None,
    min_replicas: int | None,
    max_replicas: int | None,
    env_kvs: list[str] | None,
    secret_kvs: list[str] | None,
    mounts: list[str] | None,
    container_image: str | None = None,
    container_command: list[str] | None = None,
    node_groups: list[str] | None,
    allowed_nodes_csv: str | None,
    reservation: str | None,
    allow_burst: bool | None,
    privileged: bool | None = None,
):
    # Apply simple fields
    if resource_shape is not None:
        spec.resource_shape = resource_shape
    _validate_resource_shape_nonempty(spec.resource_shape, label)

    if shared_memory_size is not None:
        spec.shared_memory_size = shared_memory_size
    _validate_shared_memory_non_negative(shared_memory_size, label)

    spec.min_replicas = 1
    if min_replicas is not None:
        if min_replicas < 0:
            console.print(
                f"[red]{label} --min-replicas must be a non-negative integer. "
                f"Found {min_replicas}.[/]"
            )
            sys.exit(1)
        spec.min_replicas = min_replicas
    if max_replicas is not None:
        if max_replicas < 0:
            console.print(
                f"[red]{label} --max-replicas must be a non-negative integer. "
                f"Found {max_replicas}.[/]"
            )
            sys.exit(1)
        spec.max_replicas = max_replicas

    # Optional envs/mounts (only set when provided to avoid overwriting file-loaded spec)
    if (env_kvs or secret_kvs) is not None and (env_kvs or secret_kvs):
        spec.envs = make_env_vars_from_strings(
            list(env_kvs or []), list(secret_kvs or [])
        )
    if mounts:
        spec.mounts = make_mounts_from_strings(list(mounts))

    if spec.container is None:
        spec.container = LeptonContainer()
    if container_image is not None:
        spec.container.image = container_image
    if container_command is not None:
        spec.container.command = container_command

    # Affinity/reservations
    _apply_affinity_and_reservation(
        spec=spec,
        node_groups=node_groups,
        reservation=reservation,
        allow_burst=allow_burst,
    )
    _validate_exactly_one_node_group(spec, label)
    _set_allowed_nodes_in_affinity(spec, allowed_nodes_csv)

    # Security context (only set when requested; do not overwrite existing)
    if privileged:
        if getattr(spec, "user_security_context", None) is None:
            spec.user_security_context = LeptonUserSecurityContext()
        spec.user_security_context.privileged = True
    return spec


@click_group()
def raycluster():
    """
    Manage Ray clusters on DGX Cloud Lepton.
    """
    pass


def _print_rayclusters_table(rayclusters) -> None:
    table = Table(title="Ray Clusters", show_lines=True, show_header=True)
    table.add_column("Name")
    table.add_column("Created At")
    table.add_column("Created By")
    table.add_column("State")
    table.add_column("Head Node Group")
    table.add_column("Head Image")
    table.add_column("Head Command")
    table.add_column("Worker Groups")
    table.add_column("Worker Node Groups")
    table.add_column("Worker Images")
    table.add_column("Worker Commands")
    table.add_column("Workers (ready/desired)")

    count = 0
    for rc in rayclusters:
        name = rc.metadata.name if rc.metadata else "-"

        created_ts = (
            datetime.fromtimestamp((rc.metadata.created_at or 0) / 1000).strftime(
                "%Y-%m-%d\n%H:%M:%S"
            )
            if rc.metadata and rc.metadata.created_at
            else "N/A"
        )
        created_by = (
            rc.metadata.created_by if rc.metadata and rc.metadata.created_by else "-"
        )

        state = rc.status.state.value if rc.status and rc.status.state else "-"

        head_node_group = (
            rc.spec.head_group_spec.affinity.allowed_dedicated_node_groups[0]
            if rc.spec
            and rc.spec.head_group_spec
            and rc.spec.head_group_spec.affinity
            and len(rc.spec.head_group_spec.affinity.allowed_dedicated_node_groups) > 0
            else "-"
        )
        # Head image/command
        head_image = (
            rc.spec.head_group_spec.container.image
            if rc.spec
            and rc.spec.head_group_spec
            and rc.spec.head_group_spec.container
            and rc.spec.head_group_spec.container.image
            else "-"
        )
        _head_cmd_val = (
            rc.spec.head_group_spec.container.command
            if rc.spec and rc.spec.head_group_spec and rc.spec.head_group_spec.container
            else None
        )
        if isinstance(_head_cmd_val, list):
            head_command = " ".join(_head_cmd_val)
        elif isinstance(_head_cmd_val, str):
            head_command = _head_cmd_val
        else:
            head_command = "-"

        # Worker groups, node groups, images, commands
        worker_group_names_list = []
        worker_node_groups_list = []
        worker_images_list = []
        worker_commands_list = []
        if rc.spec and rc.spec.worker_group_specs:
            for wg in rc.spec.worker_group_specs:
                if getattr(wg, "group_name", None):
                    worker_group_names_list.append(str(wg.group_name))
                if getattr(wg, "affinity", None) and getattr(
                    wg.affinity, "allowed_dedicated_node_groups", None
                ):
                    if len(wg.affinity.allowed_dedicated_node_groups) > 0:
                        worker_node_groups_list.append(
                            wg.affinity.allowed_dedicated_node_groups[0]
                        )
                if getattr(wg, "container", None) and getattr(
                    wg.container, "image", None
                ):
                    worker_images_list.append(wg.container.image)
                _cmd = wg.container.command if getattr(wg, "container", None) else None
                if isinstance(_cmd, list) and len(_cmd) > 0:
                    worker_commands_list.append(" ".join(_cmd))
                elif isinstance(_cmd, str) and _cmd.strip():
                    worker_commands_list.append(_cmd.strip())

        worker_group_names = (
            worker_group_names_list if len(worker_group_names_list) > 0 else "-"
        )
        worker_node_groups = (
            worker_node_groups_list if len(worker_node_groups_list) > 0 else "-"
        )
        worker_images = worker_images_list if len(worker_images_list) > 0 else "-"
        worker_commands = worker_commands_list if len(worker_commands_list) > 0 else "-"

        ready = rc.status.readyWorkerReplicas if rc.status else None
        desired = rc.status.desiredWorkerReplicas if rc.status else None
        workers_disp = f"{ready or 0}/{desired or 0}"

        table.add_row(
            f"{name}",
            created_ts,
            created_by,
            state,
            head_node_group,
            head_image,
            head_command,
            (
                ", ".join(worker_group_names)
                if isinstance(worker_group_names, list) and len(worker_group_names) > 0
                else "-"
            ),
            (
                ", ".join(worker_node_groups)
                if isinstance(worker_node_groups, list) and len(worker_node_groups) > 0
                else "-"
            ),
            (
                ", ".join(worker_images)
                if isinstance(worker_images, list) and len(worker_images) > 0
                else "-"
            ),
            (
                ", ".join(worker_commands)
                if isinstance(worker_commands, list) and len(worker_commands) > 0
                else "-"
            ),
            workers_disp,
        )
        count += 1

    if count == 0:
        console.print(
            "No Ray clusters found. Use `lep raycluster create` to create one."
        )
        return

    console.print(table)


@raycluster.command(name="list")
@click.option(
    "--name",
    "-n",
    help=(
        "Filter rayclusters by name (case-insensitive substring). Can be specified"
        " multiple times."
    ),
    type=str,
    required=False,
    multiple=True,
)
def list_command(name):
    """
    Lists all Ray clusters in the current workspace.
    """
    client = APIClient()
    rayclusters = client.raycluster.list_all()
    if name:
        lowered = [x.lower() for x in name]
        rayclusters = [
            rc
            for rc in rayclusters
            if rc.metadata
            and rc.metadata.name
            and any(n in rc.metadata.name.lower() for n in lowered)
        ]
    _print_rayclusters_table(rayclusters)


@raycluster.command(cls=WorkerGroupCommand)
@click.option(
    "--name",
    "-n",
    type=str,
    help="Name of the Ray cluster.",
    required=True,
)
@click.option(
    "--file",
    "-f",
    type=click.Path(
        exists=False,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    help=(
        "If specified, load the Ray cluster spec from this JSON file before applying "
        "additional CLI overrides. The file should contain a LeptonRayClusterUserSpec "
        "JSON produced by `lep raycluster get -p` (spec only)."
    ),
    required=False,
)
@click.option(
    "--image-pull-secrets",
    type=str,
    multiple=True,
    help="Secrets to use for pulling images.",
)
@click.option("--ray-version", type=str, help="Ray version to use.")
@click.option(
    "--head-resource-shape",
    type=str,
    help="Resource shape for the head node group.",
)
@click.option(
    "--head-shared-memory-size",
    type=int,
    help="Shared memory size for the head node group, in MiB.",
)
@click.option(
    "--head-mount",
    help=(
        "Persistent storage to be mounted to the head group, in the format "
        "`STORAGE_PATH:MOUNT_PATH:MOUNT_FROM`."
    ),
    multiple=True,
)
@click.option(
    "--head-env",
    "-he",
    help="Environment variables for the head group, in the format `NAME=VALUE`.",
    multiple=True,
)
@click.option(
    "--head-secret",
    "-hs",
    help=(
        "Secrets for the head group, in the format `NAME=SECRET_NAME`. If secret "
        "name equals the environment variable name, you can just pass `SECRET_NAME`."
    ),
    multiple=True,
)
@click.option(
    "--head-node-group",
    type=str,
    multiple=True,
    help=(
        "Dedicated node group(s) for the head node group (affinity). "
        "Only the first may be applied depending on backend support."
    ),
)
@click.option(
    "--head-allowed-nodes",
    type=str,
    help=(
        "Comma-separated node names within the specified head dedicated node group "
        "(affinity)."
    ),
)
@click.option(
    "--head-reservation",
    type=str,
    help="Reservation ID for the head node group.",
)
@click.option(
    "--head-image",
    type=str,
    help="Head group container image. Defaults to built-in default.",
)
@click.option(
    "--head-command",
    type=str,
    help="Head group container command as a single string (shlex-split).",
)
@click.option(
    "--head-allow-burst-to-other-reservation",
    type=click.BOOL,
    default=False,
    help="Allow the head node group to burst to other reservations.",
)
@click.option(
    "--head-privileged",
    type=click.BOOL,
    default=False,
    help="Run the head group container in privileged mode.",
)
@click.option(
    "--enable-autoscaler",
    type=click.BOOL,
    default=False,
    help="Enable the Ray autoscaler.",
)
@click.option(
    "--autoscaler-worker-idle-timeout",
    type=int,
    help="Timeout for worker idle timeout in seconds.",
)
@click.option(
    "--visibility",
    type=str,
    help=(
        "Visibility of the Ray cluster. Can be 'public' or 'private'. If private, "
        "the cluster will only be viewable by the creator and workspace admin."
    ),
)
def create(
    name,
    file,
    image_pull_secrets,
    ray_version,
    head_resource_shape,
    head_shared_memory_size,
    head_mount,
    head_env,
    head_secret,
    head_node_group,
    head_allowed_nodes,
    head_reservation,
    head_image,
    head_command,
    head_allow_burst_to_other_reservation,
    head_privileged,
    worker_groups,
    enable_autoscaler,
    autoscaler_worker_idle_timeout,
    visibility,
):
    """
    Creates a Ray cluster from either a spec file (spec only) or CLI flags.
    If both are provided, CLI flags override values from the file.
    """
    client = APIClient()

    # Load spec from file if provided (spec only, not full LeptonRayCluster)
    if file:
        try:
            with open(file, "r") as f:
                content = f.read()
                spec = LeptonRayClusterUserSpec.model_validate_json(content)
        except Exception as e:
            console.print(f"Cannot load Ray cluster spec from file [red]{file}[/]: {e}")
            sys.exit(1)
    else:
        spec = LeptonRayClusterUserSpec()

    # Ensure head group and container exist before applying overrides
    if spec.head_group_spec is None:
        spec.head_group_spec = RayHeadGroupSpec()
    # Validate: head must NOT contain segment_config (file-provided spec safety)
    if getattr(spec.head_group_spec, "segment_config", None) is not None:
        console.print(
            "[red]Head group does not support segment configuration"
            " (--segment-count/segment_config).[/]"
        )
        sys.exit(1)
    if spec.head_group_spec.container is None:
        spec.head_group_spec.container = LeptonContainer()

    # Resolve head image precedence: --head-image > default
    resolved_head_image = head_image if head_image else DEFAULT_RAY_IMAGE
    spec.head_group_spec.container.image = resolved_head_image

    if image_pull_secrets:
        spec.image_pull_secrets = list(image_pull_secrets)

    if ray_version is not None and resolved_head_image in DEFAULT_RAY_IMAGES:
        console.print(
            "[red]Cannot specify ray version for default image:"
            f" {resolved_head_image}.[/]"
        )
        sys.exit(1)
    spec.ray_version = DEFAULT_RAY_IMAGES.get(resolved_head_image, ray_version)

    if spec.ray_version is None or spec.ray_version == "":
        console.print("[red]Ray version is required.[/]")
        sys.exit(1)

    _build_group_spec(
        spec=spec.head_group_spec,
        label="Head",
        resource_shape=head_resource_shape,
        shared_memory_size=head_shared_memory_size,
        min_replicas=1,
        max_replicas=None,
        env_kvs=list(head_env or []),
        secret_kvs=list(head_secret or []),
        mounts=list(head_mount or []),
        container_image=resolved_head_image,
        container_command=(shlex.split(head_command) if head_command else None),
        node_groups=list(head_node_group),
        allowed_nodes_csv=head_allowed_nodes,
        reservation=head_reservation,
        allow_burst=head_allow_burst_to_other_reservation,
        privileged=head_privileged,
    )

    if worker_groups is None or len(worker_groups) == 0:
        console.print(
            "[red]At least one --worker-group is required. Legacy single-worker flags"
            " are not supported.[/]"
        )
        sys.exit(1)

    # Worker groups: build from custom-parsed worker_groups (list of dicts)
    num_groups = len(worker_groups)
    built_specs: list[RayWorkerGroupSpec] = []
    seen_worker_group_names: set[str] = set()
    for idx in range(num_groups):
        ws = RayWorkerGroupSpec()
        g = worker_groups[idx] or {}
        # per-group fields
        if g.get("group_name"):
            ws.group_name = g.get("group_name")
            if isinstance(ws.group_name, str):
                ws.group_name = ws.group_name.strip()
            if ws.group_name in seen_worker_group_names:
                console.print(
                    f"[red]Duplicate worker group name '{ws.group_name}' detected. "
                    "Each worker group must have a unique --group-name.[/]"
                )
                sys.exit(1)
            seen_worker_group_names.add(ws.group_name)
        rs_val = g.get("resource_shape")
        sms_val = (
            int(g["shared_memory_size"])
            if g.get("shared_memory_size") is not None
            else None
        )
        min_val = int(g["min_replicas"]) if g.get("min_replicas") is not None else None
        max_val = int(g["max_replicas"]) if g.get("max_replicas") is not None else None
        # segment count (only for workers)
        seg_cnt = None
        if g.get("segment_count") is not None:
            try:
                seg_cnt = int(g.get("segment_count"))
            except Exception:
                console.print(
                    "[red]--segment-count must be a positive integer (worker group"
                    f" {idx + 1}).[/]"
                )
                sys.exit(1)
            if enable_autoscaler:
                console.print(
                    "[red]--segment-count is not supported when autoscaler is"
                    " enabled.[/]"
                )
                sys.exit(1)
            if seg_cnt <= 0:
                console.print(
                    "[red]--segment-count must be a positive integer (worker group"
                    f" {idx + 1}).[/]"
                )
                sys.exit(1)
            if min_val is None:
                console.print(
                    "[red]--min-replicas is required when --segment-count is set"
                    f" (worker group {idx + 1}).[/]"
                )
                sys.exit(1)
            if min_val % seg_cnt != 0:
                console.print(
                    f"[red]--segment-count ({seg_cnt}) must evenly divide"
                    f" --min-replicas ({min_val}) (worker group {idx + 1}).[/]"
                )
                sys.exit(1)
        wimg_val = g.get("image")
        wcmd_val = g.get("command")
        wcmd_tokens = shlex.split(wcmd_val) if wcmd_val else None

        # flatten multiple occurrences, allowing comma-separated lists in each
        def _flatten_csv_list(values):
            if not values:
                return None
            out = []
            for v in values:
                if v is None:
                    continue
                parts = [x.strip() for x in str(v).split(",") if x.strip()]
                out.extend(parts)
            return out or None

        envs_list = _flatten_csv_list(g.get("env"))
        secrets_list = _flatten_csv_list(g.get("secret"))
        mounts_list = _flatten_csv_list(g.get("mount"))

        # Build the common parts
        if rs_val is None:
            console.print(
                f"[red]--resource-shape is required for worker group {idx + 1}.[/]"
            )
            sys.exit(1)
        node_group_val = g.get("node_group")
        allowed_nodes_csv = g.get("allowed_nodes")
        reservation_val = g.get("reservation")
        allow_burst_val = g.get("allow_burst")
        allow_burst_bool = (
            str(allow_burst_val).strip().lower() in {"1", "true", "yes", "y", "on"}
            if allow_burst_val is not None
            else None
        )
        privileged_val = g.get("privileged")
        privileged_bool = (
            str(privileged_val).strip().lower() in {"1", "true", "yes", "y", "on"}
            if privileged_val is not None
            else None
        )
        node_groups_list = [node_group_val] if node_group_val else None
        if not node_group_val:
            console.print(
                f"[red]--node-group is required for worker group {idx + 1}.[/]"
            )
            sys.exit(1)
        _build_group_spec(
            spec=ws,
            label="Each worker",
            resource_shape=rs_val,
            shared_memory_size=sms_val,
            min_replicas=min_val,
            max_replicas=max_val,
            env_kvs=envs_list,
            secret_kvs=secrets_list,
            mounts=mounts_list,
            container_image=wimg_val,
            container_command=wcmd_tokens,
            node_groups=node_groups_list,
            allowed_nodes_csv=allowed_nodes_csv,
            reservation=reservation_val,
            allow_burst=allow_burst_bool,
            privileged=privileged_bool,
        )
        if seg_cnt is not None:
            ws.segment_config = LeptonJobSegmentConfig(count_per_segment=seg_cnt)

        built_specs.append(ws)

        spec.worker_group_specs = built_specs

    # Autoscaler validations across groups
    if enable_autoscaler:
        if (
            autoscaler_worker_idle_timeout is None
            or autoscaler_worker_idle_timeout < 60
        ):
            console.print(
                "[red]Autoscaler worker idle timeout is required and must be greater"
                " than or equal to 60 seconds.[/]"
            )
            sys.exit(1)
        for ws in built_specs:
            if ws.max_replicas is None or ws.max_replicas <= (ws.min_replicas or 0):
                console.print(
                    "[red]Each worker must set max_replicas > min_replicas when "
                    "autoscaler is enabled.[/]"
                )
                sys.exit(1)
        spec.autoscaler = RayAutoscaler(
            ray_worker_idle_timeout=autoscaler_worker_idle_timeout,
        )
    else:
        for ws in built_specs:
            if ws.max_replicas is not None:
                console.print(
                    "[red]max_replicas is only supported when autoscaler is enabled.[/]"
                )
                sys.exit(1)

    try:
        lepton_raycluster = LeptonRayCluster(
            metadata=Metadata(
                id=name,
                name=name,
                visibility=(
                    LeptonVisibility(visibility)
                    if visibility
                    else LeptonVisibility.PUBLIC
                ),
            ),
            spec=spec,
        )
    except Exception as e:
        console.print(f"Invalid RayCluster spec: {e}")
        sys.exit(1)

    client.raycluster.create(lepton_raycluster)
    console.print(
        "🎉 [green]Ray Cluster Created Successfully![/]\n"
        f"Name: [blue]{name}[/]\n"
        f"Use `lep raycluster get -n {name}` to check the status."
    )


@raycluster.command()
@click.option("--name", "-n", help="The raycluster name to remove.", required=True)
def remove(name):
    """
    Removes a Ray cluster.
    """
    client = APIClient()
    client.raycluster.delete(name)
    console.print(f"Ray cluster [green]{name}[/] deleted successfully.")


@raycluster.command()
@click.option("--name", "-n", help="The raycluster name to stop.", required=True)
def stop(name):
    """
    Stops a Ray cluster (sets suspend=true).
    """
    client = APIClient()
    try:
        # Make sure the cluster exists; provides a nicer error if not
        _ = client.raycluster.get(name)
    except Exception as e:
        console.print(f"[red]Failed to fetch raycluster {name}: {e}[/]")
        sys.exit(1)

    try:
        spec = LeptonRayClusterUserSpec(suspend=True)
        lepton_rc = LeptonRayCluster(spec=spec)
        client.raycluster.update(name_or_raycluster=name, spec=lepton_rc)
        console.print(f"Ray cluster [green]{name}[/] stopped.")
    except Exception as e:
        console.print(f"[red]Failed to stop raycluster {name}: {e}[/]")
        sys.exit(1)


@raycluster.command()
@click.option("--name", "-n", help="The raycluster name to start.", required=True)
def start(name):
    """
    Starts a Ray cluster (sets suspend=false).
    """
    client = APIClient()
    try:
        # Make sure the cluster exists; provides a nicer error if not
        _ = client.raycluster.get(name)
    except Exception as e:
        console.print(f"[red]Failed to fetch raycluster {name}: {e}[/]")
        sys.exit(1)

    try:
        spec = LeptonRayClusterUserSpec(suspend=False)
        lepton_rc = LeptonRayCluster(spec=spec)
        client.raycluster.update(name_or_raycluster=name, spec=lepton_rc)
        console.print(f"Ray cluster [green]{name}[/] started.")
    except Exception as e:
        console.print(f"[red]Failed to start raycluster {name}: {e}[/]")
        sys.exit(1)


@raycluster.command()
@click.option("--name", "-n", help="The raycluster name to get.", required=True)
@click.option(
    "--detail",
    "-d",
    is_flag=True,
    default=False,
    help="Show the full raycluster detail.",
)
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
        "Optional local path to save the raycluster spec JSON. Directory or full"
        " filename accepted. If a directory is provided, the file will be saved as"
        " raycluster-spec-<name>.json."
    ),
    required=False,
)
def get(name, detail, path):
    """Shows Ray cluster detail and optionally saves its spec JSON."""

    client = APIClient()

    try:
        rc = client.raycluster.get(name)
    except Exception as e:
        console.print(f"[red]Failed to fetch raycluster {name}: {e}[/]")
        sys.exit(1)

    console.print(json.dumps(client.raycluster.safe_json(rc), indent=2))

    if detail:
        console.print(Pretty(rc.model_dump()))

    if path:
        spec_json = rc.spec.model_dump_json(indent=2) if rc.spec else "{}"

        try:
            save_path = resolve_save_path(path, f"raycluster-spec-{name}.json")
        except PathResolutionError as e:
            console.print(f"[red]Failed to save spec: {e}[/]")
            sys.exit(1)

        try:
            with open(save_path, "w") as f:
                f.write(spec_json)
            console.print(f"Ray cluster spec saved to [green]{save_path}[/].")
        except Exception as e:
            console.print(f"[red]Failed to save spec: {e}[/]")
            sys.exit(1)


@raycluster.command(cls=WorkerGroupCommand)
@click.option("--name", "-n", help="The raycluster name to update.", required=True)
def update(name, worker_groups):
    """
    Updates one or more Ray worker groups' replica settings.
    - Start a worker group definition with -wg/--worker-group and follow it with per-group flags:
      --group-name, --min-replicas, --max-replicas, --segment-count
    - If --group-name is omitted and there is exactly one existing worker group and one -wg block, it is inferred.
    - --max-replicas is only allowed when autoscaler is enabled, and must be greater than --min-replicas.
    - --segment-count is only allowed when autoscaler is disabled, must be positive, and must evenly divide --min-replicas.
    """
    client = APIClient()

    # Fetch existing cluster to infer worker group name
    try:
        existing_rc = client.raycluster.get(name)
    except Exception as e:
        console.print(f"[red]Failed to fetch raycluster {name}: {e}[/]")
        sys.exit(1)

    if not existing_rc.spec or not existing_rc.spec.worker_group_specs:
        console.print("[red]Existing raycluster has no worker groups to update.[/]")
        sys.exit(1)

    autoscaler_enabled = bool(getattr(existing_rc.spec, "autoscaler", None))

    # Require at least one worker group definition parsed by the custom command
    if worker_groups is None or len(worker_groups) == 0:
        console.print(
            "[red]At least one worker group update is required. Use -wg followed by"
            " per-group flags like"
            " --group-name/--min-replicas/--max-replicas/--segment-count.[/]"
        )
        sys.exit(1)

    # Validate target groups exist
    existing_names = [
        wg.group_name
        for wg in existing_rc.spec.worker_group_specs or []
        if getattr(wg, "group_name", None)
    ]

    update_specs: list[RayWorkerGroupSpec] = []
    updated_group_names: list[str] = []
    num_groups = len(worker_groups)
    for idx in range(num_groups):
        g = worker_groups[idx] or {}
        gn = g.get("group_name")
        mr = int(g["min_replicas"]) if g.get("min_replicas") is not None else None
        xr = int(g["max_replicas"]) if g.get("max_replicas") is not None else None
        sc = int(g["segment_count"]) if g.get("segment_count") is not None else None

        # Infer group name when omitted and there is exactly one existing worker group,
        # and only a single update is being requested.
        if gn is None:
            if num_groups == 1 and len(existing_names) == 1:
                gn = existing_names[0]
            else:
                console.print(
                    "[red]--group-name is required for each group when multiple worker"
                    " groups exist or multiple updates are provided.[/]"
                )
                sys.exit(1)

        if gn not in existing_names:
            console.print(
                f"[red]Worker group '{gn}' not found in this raycluster. "
                f"Available: {', '.join(existing_names) if existing_names else '-'}[/]"
            )
            sys.exit(1)

        if mr is None or not isinstance(mr, int) or mr < 0:
            console.print(
                "[red]--min-replicas is required and must be a non-negative integer"
                f" (group: {gn}).[/]"
            )
            sys.exit(1)

        if xr is not None:
            if not autoscaler_enabled:
                console.print(
                    "[red]--max-replicas is only supported when autoscaler is"
                    " enabled.[/]"
                )
                sys.exit(1)
            if not isinstance(xr, int) or xr <= mr:
                console.print(
                    "[red]--max-replicas must be an integer greater than"
                    f" --min-replicas (group: {gn}).[/]"
                )
                sys.exit(1)

        # Validate segment count if provided
        if sc is not None:
            if autoscaler_enabled:
                console.print(
                    "[red]--segment-count is not supported when autoscaler is"
                    " enabled.[/]"
                )
                sys.exit(1)
            if not isinstance(sc, int) or sc <= 0:
                console.print(
                    f"[red]--segment-count must be a positive integer (group: {gn}).[/]"
                )
                sys.exit(1)
            if mr is None:
                console.print(
                    "[red]--min-replicas is required when --segment-count is provided"
                    f" (group: {gn}).[/]"
                )
                sys.exit(1)
            if mr % sc != 0:
                console.print(
                    f"[red]--segment-count ({sc}) must evenly divide --min-replicas"
                    f" ({mr}) (group: {gn}).[/]"
                )
                sys.exit(1)

        update_specs.append(
            RayWorkerGroupSpec(
                group_name=gn,
                min_replicas=mr,
                max_replicas=(xr if xr is not None else None),
            )
        )
        if sc is not None:
            update_specs[-1].segment_config = LeptonJobSegmentConfig(
                count_per_segment=sc
            )
        updated_group_names.append(gn)

    spec = LeptonRayClusterUserSpec(worker_group_specs=update_specs)

    lepton_rc = LeptonRayCluster(spec=spec)
    client.raycluster.update(name_or_raycluster=name, spec=lepton_rc)
    console.print(
        f"Ray cluster [green]{name}[/] worker group(s)"
        f" [blue]{', '.join(updated_group_names)}[/] updated."
    )


@raycluster.command(name="submit-job")
@click.option(
    "--name", "-n", help="The raycluster name to submit a job to.", required=True
)
@click.option(
    "--submission-id",
    type=str,
    required=False,
    help="Submission ID to specify for the job.",
)
@click.option(
    "--runtime-env",
    type=click.Path(
        exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True
    ),
    required=False,
    help="Path to a YAML file containing a runtime_env definition.",
)
@click.option(
    "--runtime-env-json",
    type=str,
    required=False,
    help="JSON-serialized runtime_env dictionary.",
)
@click.option(
    "--working-dir",
    type=str,
    required=False,
    help=(
        "Directory or remote URI (.zip) for working_dir. If specified, overrides the "
        "option in --runtime-env."
    ),
)
@click.option(
    "--metadata-json",
    type=str,
    required=False,
    help="JSON-serialized dictionary of metadata to attach to the job.",
)
@click.option(
    "--entrypoint-num-cpus",
    type=float,
    required=False,
    help="CPU cores to reserve for entrypoint.",
)
@click.option(
    "--entrypoint-num-gpus",
    type=float,
    required=False,
    help="GPUs to reserve for entrypoint.",
)
@click.option(
    "--entrypoint-memory",
    type=int,
    required=False,
    help="Memory (bytes) to reserve for entrypoint.",
)
@click.option(
    "--entrypoint-resources",
    type=str,
    required=False,
    help="JSON-serialized dict of custom resources to reserve for entrypoint.",
)
@click.option(
    "--no-wait",
    is_flag=True,
    default=False,
    help="Do not stream logs or wait for job completion.",
)
@click.argument("entrypoint", nargs=-1, type=click.UNPROCESSED)
def submit_job(
    name,
    submission_id,
    runtime_env,
    runtime_env_json,
    working_dir,
    metadata_json,
    entrypoint_num_cpus,
    entrypoint_num_gpus,
    entrypoint_memory,
    entrypoint_resources,
    no_wait,
    entrypoint,
):
    """
    Submits a job to a Ray cluster.

    Usage: lep raycluster submit-job -n <cluster> -- <entrypoint command>
    Everything after "--" is treated as the entrypoint command, just like native Ray.
    """
    base_client = APIClient()

    try:
        _ = base_client.raycluster.get(name)
    except Exception as e:
        console.print(f"[red]Failed to fetch raycluster {name}: {e}[/]")
        sys.exit(1)

    # Determine address (use cluster dashboard URL)
    ray_head_dashboard_url = f"{base_client.url}/rayclusters/{name}/dashboard"

    # Suppress urllib3 InsecureRequestWarning when verify=False (unverified HTTPS)
    warnings.filterwarnings(
        "ignore",
        category=urllib3.exceptions.InsecureRequestWarning,
    )

    submission_client = JobSubmissionClient(
        address=ray_head_dashboard_url,
        headers={
            "Authorization": f"Bearer {base_client.token()}",
            "origin": base_client.get_dashboard_base_url(),
        },
        verify=False,  # TODO: make this more secure
    )

    if not entrypoint or len(entrypoint) == 0:
        console.print("[red]Entry point command is required. Provide it after -- .[/]")
        sys.exit(1)

    entrypoint_cmd = shlex.join(entrypoint)

    # Build runtime_env
    runtime_env_dict = None
    if runtime_env and runtime_env_json:
        console.print(
            "[red]Specify only one of --runtime-env or --runtime-env-json.[/]"
        )
        sys.exit(1)
    if runtime_env:
        try:
            with open(runtime_env, "r") as f:
                runtime_env_dict = yaml.safe_load(f) or {}
            if not isinstance(runtime_env_dict, dict):
                raise ValueError("runtime_env must be a mapping")
        except Exception as e:
            console.print(f"[red]Failed to load runtime_env YAML: {e}[/]")
            sys.exit(1)
    if runtime_env_json:
        try:
            runtime_env_dict = json.loads(runtime_env_json)
            if not isinstance(runtime_env_dict, dict):
                raise ValueError("runtime_env JSON must be a dict")
        except Exception as e:
            console.print(f"[red]Failed to parse runtime_env JSON: {e}[/]")
            sys.exit(1)
    if working_dir:
        runtime_env_dict = runtime_env_dict or {}
        runtime_env_dict["working_dir"] = working_dir

    # Build metadata
    metadata_dict = None
    if metadata_json:
        try:
            metadata_dict = json.loads(metadata_json)
            if not isinstance(metadata_dict, dict):
                raise ValueError("metadata JSON must be a dict")
        except Exception as e:
            console.print(f"[red]Failed to parse metadata JSON: {e}[/]")
            sys.exit(1)

    # Build entrypoint resources
    entrypoint_resources_dict = None
    if entrypoint_resources:
        try:
            entrypoint_resources_dict = json.loads(entrypoint_resources)
            if not isinstance(entrypoint_resources_dict, dict):
                raise ValueError("entrypoint_resources must be a dict")
        except Exception as e:
            console.print(f"[red]Failed to parse entrypoint_resources JSON: {e}[/]")
            sys.exit(1)

    try:
        submit_kwargs = dict(entrypoint=entrypoint_cmd)
        if submission_id is not None:
            submit_kwargs["submission_id"] = submission_id
        if runtime_env_dict is not None:
            submit_kwargs["runtime_env"] = runtime_env_dict
        if metadata_dict is not None:
            submit_kwargs["metadata"] = metadata_dict
        if entrypoint_num_cpus is not None:
            submit_kwargs["entrypoint_num_cpus"] = entrypoint_num_cpus
        if entrypoint_num_gpus is not None:
            submit_kwargs["entrypoint_num_gpus"] = entrypoint_num_gpus
        if entrypoint_memory is not None:
            submit_kwargs["entrypoint_memory"] = entrypoint_memory
        if entrypoint_resources_dict is not None:
            submit_kwargs["entrypoint_resources"] = entrypoint_resources_dict
        job_id_ret = submission_client.submit_job(**submit_kwargs)
        console.print(
            f"Job submitted to [green]{name}[/] with id [blue]{job_id_ret}[/]."
        )
    except Exception as e:
        console.print(f"[red]Failed to submit job to {name}: {e}[/]")
        sys.exit(1)

    if no_wait:
        return

    console.print(f"Streaming logs for job [blue]{job_id_ret}[/] (Ctrl+C to stop)...")
    try:

        async def _stream_logs() -> None:
            async for chunk in submission_client.tail_job_logs(job_id_ret):
                sys.stdout.write(chunk)
                sys.stdout.flush()

        asyncio.run(_stream_logs())
    except KeyboardInterrupt:
        console.print("\n[yellow]Log streaming interrupted by user.[/]")
        return
    except Exception as e:
        console.print(f"[red]Failed to stream logs: {e}[/]")

    try:
        status = submission_client.get_job_status(job_id_ret)
        console.print(
            f"Job [blue]{job_id_ret}[/] finished with status: [green]{status.value}[/]"
        )
        if status != JobStatus.SUCCEEDED:
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Failed to retrieve job status: {e}[/]")


@raycluster.command(name="stop-job")
@click.option(
    "--name", "-n", help="The raycluster name that hosts the job.", required=True
)
@click.option(
    "--job-id",
    "-j",
    type=str,
    required=True,
    help="The Ray job ID to stop.",
)
def stop_job_command(name, job_id):
    """
    Stops a Ray job by job ID on a given Ray cluster.
    """
    base_client = APIClient()

    # Ensure cluster exists
    try:
        _ = base_client.raycluster.get(name)
    except Exception as e:
        console.print(f"[red]Failed to fetch raycluster {name}: {e}[/]")
        sys.exit(1)

    # Determine address (use cluster dashboard URL)
    ray_head_dashboard_url = f"{base_client.url}/rayclusters/{name}/dashboard"

    # Suppress urllib3 InsecureRequestWarning when verify=False (unverified HTTPS)
    warnings.filterwarnings(
        "ignore",
        category=urllib3.exceptions.InsecureRequestWarning,
    )

    submission_client = JobSubmissionClient(
        address=ray_head_dashboard_url,
        headers={
            "Authorization": f"Bearer {base_client.token()}",
            "origin": base_client.get_dashboard_base_url(),
        },
        verify=False,  # TODO: make this more secure
    )

    try:
        submission_client.stop_job(job_id)
        console.print(
            f"Requested stop for job [blue]{job_id}[/] on cluster [green]{name}[/]."
        )
    except Exception as e:
        console.print(f"[red]Failed to stop job {job_id} on {name}: {e}[/]")
        sys.exit(1)


@raycluster.command(name="list-jobs")
@click.option(
    "--name", "-n", help="The raycluster name to list jobs for.", required=True
)
def list_jobs_command(name):
    """
    Lists Ray jobs on a given Ray cluster.
    """
    base_client = APIClient()

    try:
        _ = base_client.raycluster.get(name)
    except Exception as e:
        console.print(f"[red]Failed to fetch raycluster {name}: {e}[/]")
        sys.exit(1)

    ray_head_dashboard_url = f"{base_client.url}/rayclusters/{name}/dashboard"

    warnings.filterwarnings(
        "ignore",
        category=urllib3.exceptions.InsecureRequestWarning,
    )

    submission_client = JobSubmissionClient(
        address=ray_head_dashboard_url,
        headers={
            "Authorization": f"Bearer {base_client.token()}",
            "origin": base_client.get_dashboard_base_url(),
        },
        verify=False,
    )

    try:
        jobs = submission_client.list_jobs() or []
    except Exception as e:
        console.print(f"[red]Failed to list jobs on {name}: {e}[/]")
        sys.exit(1)

    if not jobs:
        console.print("No Ray jobs found on this cluster.")
        return

    def _fmt_ts_ms(ts_ms):
        if ts_ms is None:
            return "N/A"
        try:
            return datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(ts_ms)

    table = Table(title=f"Jobs on {name}", show_lines=True, show_header=True)
    table.add_column("Job ID")
    table.add_column("Status")
    table.add_column("Entrypoint")
    table.add_column("Start")
    table.add_column("End")
    table.add_column("Message")

    for j in jobs:
        job_id_disp = (
            getattr(j, "submission_id", None) or getattr(j, "job_id", "-") or "-"
        )
        status_disp = getattr(j, "status", None)
        status_str = (
            status_disp.value
            if hasattr(status_disp, "value")
            else str(status_disp or "-")
        )
        entrypoint = getattr(j, "entrypoint", None) or "-"
        start_str = _fmt_ts_ms(getattr(j, "start_time", None))
        end_str = _fmt_ts_ms(getattr(j, "end_time", None))
        message = getattr(j, "message", None) or "-"
        table.add_row(job_id_disp, status_str, entrypoint, start_str, end_str, message)

    console.print(table)


def add_command(cli_group):
    cli_group.add_command(raycluster, name="raycluster")
