import json
import shlex
from datetime import datetime
import sys
import warnings
import urllib3
import yaml
import asyncio

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
from ..api.v1.types.common import LeptonVisibility, Metadata
from ..api.v1.types.raycluster import (
    LeptonRayCluster,
    LeptonRayClusterUserSpec,
    RayHeadGroupSpec,
    RayWorkerGroupSpec,
    RayAutoscaler,
)
from ..api.v1.photon import make_mounts_from_strings, make_env_vars_from_strings

DEFAULT_RAY_IMAGE = "ray:2.48.0-py312-gpu"
DEFAULT_RAY_IMAGES = {
    "ray:2.46.0": "2.46.0",
    "ray:2.46.0-py310-gpu": "2.46.0",
    "ray:2.46.0-py311-gpu": "2.46.0",
    "ray:2.46.0-py312-gpu": "2.46.0",
    "ray:2.47.0": "2.47.0",
    "ray:2.47.0-py310-gpu": "2.47.0",
    "ray:2.47.0-py311-gpu": "2.47.0",
    "ray:2.47.0-py312-gpu": "2.47.0",
    "ray:2.48.0": "2.48.0",
    "ray:2.48.0-py310-gpu": "2.48.0",
    "ray:2.48.0-py311-gpu": "2.48.0",
    "ray:2.48.0-py312-gpu": "2.48.0",
}


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
    table.add_column("Worker Group Name")
    table.add_column("Workers (ready/desired)")
    table.add_column("Worker Node Group")
    table.add_column("Ray Image")

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
        worker_group_names = (
            [wg.group_name for wg in rc.spec.worker_group_specs]
            if rc.spec and rc.spec.worker_group_specs
            else "-"
        )
        worker_node_groups = (
            [
                wg.affinity.allowed_dedicated_node_groups[0]
                for wg in rc.spec.worker_group_specs
                if wg.affinity and len(wg.affinity.allowed_dedicated_node_groups) > 0
            ]
            if rc.spec and rc.spec.worker_group_specs
            else "-"
        )

        ready = rc.status.readyWorkerReplicas if rc.status else None
        desired = rc.status.desiredWorkerReplicas if rc.status else None
        workers_disp = f"{ready or 0}/{desired or 0}"

        ray_image = rc.spec.image if rc.spec and rc.spec.image else "-"

        table.add_row(
            f"{name}",
            created_ts,
            created_by,
            state,
            head_node_group,
            (
                ", ".join(worker_group_names)
                if isinstance(worker_group_names, list) and len(worker_group_names) > 0
                else "-"
            ),
            workers_disp,
            (
                ", ".join(worker_node_groups)
                if isinstance(worker_node_groups, list) and len(worker_node_groups) > 0
                else "-"
            ),
            ray_image,
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


@raycluster.command()
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
    "--image",
    type=str,
    help=f"Ray cluster container image. Default: {DEFAULT_RAY_IMAGE}",
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
    "--head-allow-burst-to-other-reservation",
    type=click.BOOL,
    default=False,
    help="Allow the head node group to burst to other reservations.",
)
@click.option(
    "--worker-group-name",
    type=str,
    help="Name of the worker group (if specifying via flags).",
)
@click.option(
    "--worker-resource-shape",
    type=str,
    help="Resource shape for the worker node group.",
)
@click.option(
    "--worker-shared-memory-size",
    type=int,
    help="Shared memory size for the worker node group, in MiB.",
)
@click.option(
    "--worker-mount",
    help=(
        "Persistent storage to be mounted to the worker group, in the format "
        "`STORAGE_PATH:MOUNT_PATH:MOUNT_FROM`."
    ),
    multiple=True,
)
@click.option(
    "--worker-env",
    "-we",
    help="Environment variables for the worker group, in the format `NAME=VALUE`.",
    multiple=True,
)
@click.option(
    "--worker-secret",
    "-ws",
    help=(
        "Secrets for the worker group, in the format `NAME=SECRET_NAME`. If secret "
        "name equals the environment variable name, you can just pass `SECRET_NAME`."
    ),
    multiple=True,
)
@click.option(
    "--worker-node-group",
    type=str,
    multiple=True,
    help=(
        "Dedicated node group(s) for the worker node group (affinity). "
        "Only the first may be applied depending on backend support."
    ),
)
@click.option(
    "--worker-allowed-nodes",
    type=str,
    help=(
        "Comma-separated node names within the specified worker dedicated node group "
        "(affinity)."
    ),
)
@click.option(
    "--worker-reservation",
    type=str,
    help="Reservation ID for the worker node group.",
)
@click.option(
    "--worker-allow-burst-to-other-reservation",
    type=click.BOOL,
    default=False,
    help="Allow the worker node group to burst to other reservations.",
)
@click.option(
    "--worker-min-replicas",
    type=int,
    help="Minimum replicas for the worker node group. Default: 1",
)
@click.option(
    "--worker-max-replicas",
    type=int,
    help="Maximum replicas for the worker node group.",
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
    image,
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
    head_allow_burst_to_other_reservation,
    worker_group_name,
    worker_resource_shape,
    worker_shared_memory_size,
    worker_mount,
    worker_env,
    worker_secret,
    worker_node_group,
    worker_allowed_nodes,
    worker_reservation,
    worker_allow_burst_to_other_reservation,
    worker_min_replicas,
    worker_max_replicas,
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

    # Top-level spec overrides
    spec.image = DEFAULT_RAY_IMAGE
    if image is not None:
        spec.image = image

    if image_pull_secrets:
        spec.image_pull_secrets = list(image_pull_secrets)

    if ray_version is not None and spec.image in DEFAULT_RAY_IMAGES:
        console.print(
            f"[red]Cannot specify ray version for default image: {spec.image}.[/]"
        )
        sys.exit(1)
    spec.ray_version = DEFAULT_RAY_IMAGES.get(spec.image, ray_version)

    if spec.ray_version is None or spec.ray_version == "":
        console.print("[red]Ray version is required.[/]")
        sys.exit(1)

    # Head group spec overrides and validation
    if spec.head_group_spec is None:
        spec.head_group_spec = RayHeadGroupSpec()

    if head_resource_shape is not None:
        spec.head_group_spec.resource_shape = head_resource_shape

    if (
        spec.head_group_spec.resource_shape is None
        or spec.head_group_spec.resource_shape == ""
    ):
        console.print("[red]Head resource shape is required.[/]")
        sys.exit(1)

    if head_shared_memory_size is not None:
        spec.head_group_spec.shared_memory_size = head_shared_memory_size
    if head_shared_memory_size is not None and head_shared_memory_size < 0:
        console.print("[red]Head shared memory size must be non-negative.[/]")
        sys.exit(1)

    spec.head_group_spec.min_replicas = 1
    # Head envs and mounts (only override when flags supplied)
    if head_env or head_secret:
        spec.head_group_spec.envs = make_env_vars_from_strings(
            list(head_env or []), list(head_secret or [])
        )
    if head_mount:
        spec.head_group_spec.mounts = make_mounts_from_strings(list(head_mount))

    # Resolve head node group names to IDs via shared utility when provided via flags
    if head_node_group is None or head_node_group == "":
        console.print("[red]Head node group is required.[/]")
        sys.exit(1)

    apply_nodegroup_and_queue_config(
        spec=spec.head_group_spec,
        node_groups=list(head_node_group),
        node_ids=None,
        queue_priority=None,
        can_be_preempted=None,
        can_preempt=None,
        with_reservation=head_reservation,
        allow_burst=head_allow_burst_to_other_reservation,
    )
    # Validate head node group presence and cardinality
    if (
        not spec.head_group_spec.affinity
        or not spec.head_group_spec.affinity.allowed_dedicated_node_groups
        or len(spec.head_group_spec.affinity.allowed_dedicated_node_groups) != 1
    ):
        console.print("[red]Head node group is required and must be exactly one.[/]")
        sys.exit(1)

    if head_allowed_nodes:
        head_nodes_flat: list[str] = [
            x.strip() for x in head_allowed_nodes.split(",") if x.strip()
        ]
        if head_nodes_flat:
            spec.head_group_spec.affinity.allowed_nodes_in_node_group = head_nodes_flat

    # Worker group: ensure exists, apply overrides, validate shape, then apply affinity/name/replicas
    if spec.worker_group_specs is None or len(spec.worker_group_specs) == 0:
        spec.worker_group_specs = [RayWorkerGroupSpec()]

    if len(spec.worker_group_specs) != 1:
        console.print("[red]Only one worker group is supported.[/]")
        sys.exit(1)

    worker_spec = spec.worker_group_specs[0]

    # Worker envs and mounts (only override when flags supplied)
    if worker_env or worker_secret:
        worker_spec.envs = make_env_vars_from_strings(
            list(worker_env or []), list(worker_secret or [])
        )
    if worker_mount:
        worker_spec.mounts = make_mounts_from_strings(list(worker_mount))

    if worker_group_name is not None:
        worker_spec.group_name = worker_group_name
    if worker_resource_shape is not None:
        worker_spec.resource_shape = worker_resource_shape

    if worker_spec.resource_shape is None or worker_spec.resource_shape == "":
        console.print("[red]Worker resource shape is required.[/]")
        sys.exit(1)

    if worker_shared_memory_size is not None:
        worker_spec.shared_memory_size = worker_shared_memory_size
    if worker_shared_memory_size is not None and worker_shared_memory_size < 0:
        console.print("[red]Worker shared memory size must be non-negative.[/]")
        sys.exit(1)

    worker_spec.min_replicas = 1
    if worker_min_replicas is not None:
        worker_spec.min_replicas = worker_min_replicas
    if worker_spec.min_replicas is None or worker_spec.min_replicas <= 0:
        console.print(
            "[red]Worker min replicas is required and must be a positive integer.[/]"
        )
        sys.exit(1)

    # Resolve worker node group names to IDs via shared utility when provided via flags
    if worker_node_group is None or worker_node_group == "":
        console.print("[red]Worker node group is required.[/]")
        sys.exit(1)

    apply_nodegroup_and_queue_config(
        spec=worker_spec,
        node_groups=list(worker_node_group),
        node_ids=None,
        queue_priority=None,
        can_be_preempted=None,
        can_preempt=None,
        with_reservation=worker_reservation,
        allow_burst=worker_allow_burst_to_other_reservation,
    )
    # Validate worker node group presence and cardinality
    if (
        not worker_spec.affinity
        or not worker_spec.affinity.allowed_dedicated_node_groups
        or len(worker_spec.affinity.allowed_dedicated_node_groups) != 1
    ):
        console.print("[red]Worker node group is required and must be exactly one.[/]")
        sys.exit(1)

    if worker_allowed_nodes:
        worker_nodes_flat: list[str] = [
            x.strip() for x in worker_allowed_nodes.split(",") if x.strip()
        ]
        if worker_nodes_flat:
            worker_spec.affinity.allowed_nodes_in_node_group = worker_nodes_flat

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

        if (
            worker_max_replicas is None
            or worker_max_replicas <= worker_spec.min_replicas
        ):
            console.print(
                "[red]Worker max replicas is required and must be greater than worker"
                " min replicas when autoscaler is enabled.[/]"
            )
            sys.exit(1)

        worker_spec.max_replicas = worker_max_replicas
        spec.autoscaler = RayAutoscaler(
            ray_worker_idle_timeout=autoscaler_worker_idle_timeout,
        )
    else:
        if worker_max_replicas is not None:
            console.print(
                "[red]Worker max replicas is only supported when autoscaler is"
                " enabled.[/]"
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


@raycluster.command()
@click.option("--name", "-n", help="The raycluster name to update.", required=True)
@click.option(
    "--min-replicas",
    type=int,
    required=True,
    help="New minimum replicas for the worker group.",
)
def update(name, min_replicas):
    """
    Updates a Ray cluster worker group's min replicas.
    The worker group name is inferred from the existing cluster when there is
    exactly one worker group.
    """
    client = APIClient()

    # Fetch existing cluster to infer worker group name
    try:
        existing_rc = client.raycluster.get(name)
    except Exception as e:
        console.print(f"[red]Failed to fetch raycluster {name}: {e}[/]")
        sys.exit(1)

    # Ensure the existing cluster has exactly one worker group
    if (
        not existing_rc.spec
        or not existing_rc.spec.worker_group_specs
        or len(existing_rc.spec.worker_group_specs) != 1
    ):
        console.print(
            "[red]This command supports clusters with exactly one worker group.[/]"
        )
        sys.exit(1)

    # Extract existing worker group name and build a minimal user spec with new min_replicas
    existing_wg = existing_rc.spec.worker_group_specs[0]
    group_name = existing_wg.group_name if existing_wg else None
    if group_name is None or not isinstance(group_name, str) or group_name == "":
        console.print(
            "[red]Existing worker group must have a valid non-empty group_name.[/]"
        )
        sys.exit(1)

    if min_replicas is None or not isinstance(min_replicas, int) or min_replicas <= 0:
        console.print(
            "[red]--min-replicas is required and must be a positive integer.[/]"
        )
        sys.exit(1)

    spec = LeptonRayClusterUserSpec(
        worker_group_specs=[
            RayWorkerGroupSpec(
                group_name=group_name,
                min_replicas=min_replicas,
            )
        ]
    )

    lepton_rc = LeptonRayCluster(spec=spec)
    client.raycluster.update(name_or_raycluster=name, spec=lepton_rc)
    console.print(f"Ray cluster [green]{name}[/] updated.")


@raycluster.command()
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
def submit(
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

    Usage: lep raycluster submit -n <cluster> -- <entrypoint command>
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


def add_command(cli_group):
    cli_group.add_command(raycluster, name="raycluster")
