"""
`lep dynamo`: manage Dynamo graph deployments (multi-service LLM inference
graphs served by NVIDIA Dynamo with a vLLM, SGLang, or TensorRT-LLM backend).

The command surface mirrors the dashboard's Dynamo pages: list, create, edit
(merge patch), detail/status, per-service detail and restart, per-service
replicas, replica logs, replica deletion, metrics, and history.
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import click
from rich.pretty import Pretty
from rich.table import Table

from ..api.v2.api_resource import ClientError, ServerError
from ..api.v2.client import APIClient
from ..api.v2.dynamo_patch import (
    apply_merge_patch,
    build_merge_patch,
    deep_merge_patch,
    spec_to_dict,
)
from ..api.v2.dynamo_spec import (
    DYNAMO_FRAMEWORKS,
    DYNAMO_RUNTIME_IMAGES,
    DYNAMO_SERVING_MODES,
    DYNAMO_VERSION,
    DynamoServiceInput,
    SUPPORTED_DYNAMO_VERSIONS,
    build_dynamo_spec,
    build_service_spec,
    command_display_string,
    frontend_node_groups_of,
    serving_mode_from_services,
    sort_service_names,
    validate_dynamo_name,
    validate_ingress_timeout,
)
from ..api.v2.spec_utils import make_env_vars_from_strings
from ..api.v2.types.common import LeptonVisibility, Metadata
from ..api.v2.types.dynamo import (
    DYNAMO_FRONTEND_SERVICE,
    DYNAMO_SERVICE_NAMES,
    DynamoReplica,
    LeptonDynamoGraphDeployment,
    LeptonDynamoGraphDeploymentUserSpec,
    LeptonDynamoServiceSpec,
)
from .util import (
    PathResolutionError,
    check,
    click_group,
    colorize_state,
    console,
    format_timestamp_ms,
    make_block_option_command,
    make_name_id_cell,
    resolve_save_path,
)

# Deployment-level metrics shown by the dashboard's Metrics tab.
DEPLOYMENT_METRICS = (
    "GPUUtilAvg",
    "GPUMemoryUtilAvg",
    "GPUMemoryUsageMax",
    "GPUMemoryTotal",
    "GPUTempAvg",
)
# Replica-level metrics shown by the dashboard's per-replica metrics view.
REPLICA_METRICS = (
    "CPUUtil",
    "memoryUtil",
    "memoryUsage",
    "memoryTotal",
    "GPUUtil",
    "GPUMemoryUtil",
    "GPUMemoryUsage",
    "GPUMemoryTotal",
    "GPUPowerConsumption",
)
METRIC_WINDOWS = ("1", "2", "3", "6", "12", "24")


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _fmt_ts(ms: Optional[int]) -> str:
    if not ms:
        return "-"
    try:
        return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "-"


def _state_text(state) -> str:
    if state is None:
        return "-"
    return str(getattr(state, "value", state))


def _normalize_token(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _colorize_health(health: Optional[str]) -> str:
    if not health:
        return "-"
    lowered = health.lower()
    if lowered == "healthy":
        return f"[green]{health}[/]"
    if lowered == "degraded":
        return f"[yellow]{health}[/]"
    return f"[red]{health}[/]"


_READINESS_GREEN = {"Ready"}
_READINESS_BLUE = {"InProgress", "Migrating", "RequireReadinessApproval"}
_READINESS_AMBER = {
    "Queueing",
    "NoCapacity",
    "WaitingForCapacity",
    "Deleting",
    "Preempting",
}
_READINESS_RED = {
    "UserCodeError",
    "SystemError",
    "DeploymentConfigError",
    "ConfigError",
    "Failed",
}


def _replica_reason(replica: DynamoReplica) -> str:
    issue = replica.status.readiness_issue if replica.status else None
    if issue is None or issue.reason is None:
        return "Terminated"
    return _state_text(issue.reason)


def _colorize_readiness(reason: str) -> str:
    if reason in _READINESS_GREEN:
        return f"[green]{reason}[/]"
    if reason in _READINESS_BLUE:
        return f"[blue]{reason}[/]"
    if reason in _READINESS_AMBER:
        return f"[yellow]{reason}[/]"
    if reason in _READINESS_RED:
        return f"[red]{reason}[/]"
    return f"[bright_black]{reason}[/]"


def _node_groups_of(spec: Optional[LeptonDynamoGraphDeploymentUserSpec]) -> List[str]:
    seen: List[str] = []
    for name in sort_service_names(list((spec.services if spec else None) or {})):
        service = spec.services[name]  # type: ignore[index]
        groups = (
            service.affinity.allowed_dedicated_node_groups if service.affinity else None
        ) or []
        for group in groups:
            if group not in seen:
                seen.append(group)
    return seen


def _env_summary(envs) -> str:
    if not envs:
        return "-"
    parts = []
    for env in envs:
        if env.value_from and env.value_from.secret_name_ref:
            parts.append(f"{env.name} (secret: {env.value_from.secret_name_ref})")
        else:
            parts.append(env.name)
    return ", ".join(parts)


def _main_container(service: Optional[LeptonDynamoServiceSpec]):
    if service is None or service.extra_pod_spec is None:
        return None
    return service.extra_pod_spec.main_container


def _service_summary_line(
    name: str,
    service: LeptonDynamoServiceSpec,
    status_services: Optional[Dict[str, Any]],
) -> str:
    replicas = service.min_replicas if service.min_replicas is not None else 0
    shape = service.resource_shape or "unknown-shape"
    line = f"{name}: {replicas} x {shape}"
    status = (status_services or {}).get(name)
    if status is not None and (
        status.ready_replicas is not None or status.desired_replicas is not None
    ):
        line += f" ({status.ready_replicas or 0}/{status.desired_replicas or 0} ready)"
    return line


def _sorted_services(dep: LeptonDynamoGraphDeployment) -> List[str]:
    return sort_service_names(list((dep.spec.services if dep.spec else None) or {}))


def _confirm(prompt: str, yes: bool) -> None:
    if yes:
        return
    if not click.confirm(prompt, default=False):
        console.print("Aborted.")
        sys.exit(0)


def _load_json_file(path: str, what: str) -> Any:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        console.print(f"Cannot load {what} from file [red]{path}[/]: {e}")
        sys.exit(1)


def _load_user_spec_file(path: str) -> LeptonDynamoGraphDeploymentUserSpec:
    """Accept either a bare user spec (`lep dynamo get -p`) or a full object."""
    payload = _load_json_file(path, "Dynamo deployment spec")
    if isinstance(payload, dict) and "spec" in payload and "services" not in payload:
        payload = payload["spec"]
    try:
        return LeptonDynamoGraphDeploymentUserSpec.model_validate(payload)
    except Exception as e:
        console.print(f"Invalid Dynamo deployment spec in [red]{path}[/]: {e}")
        sys.exit(1)


def _resolve_node_group_ids(client: APIClient, terms: Sequence[str]) -> List[str]:
    """Map dedicated node group names or IDs to IDs; exit on unknown values."""
    if not terms:
        return []
    node_groups = client.nodegroup.list_all()
    by_key: Dict[str, str] = {}
    for ng in node_groups:
        if ng.metadata is None:
            continue
        if ng.metadata.id_:
            by_key[ng.metadata.id_] = ng.metadata.id_
        if ng.metadata.name:
            by_key.setdefault(ng.metadata.name, ng.metadata.id_ or ng.metadata.name)
    resolved: List[str] = []
    for term in terms:
        if term not in by_key:
            available = ", ".join(
                sorted(
                    f"{ng.metadata.name} ({ng.metadata.id_})"
                    for ng in node_groups
                    if ng.metadata
                )
            )
            console.print(
                f"Invalid node group: [red]{term}[/] (valid node groups: {available})"
            )
            sys.exit(1)
        if by_key[term] not in resolved:
            resolved.append(by_key[term])
    return resolved


def _lookup_shape_gpu_count(
    client: APIClient, node_group_id: Optional[str], resource_shape: Optional[str]
) -> Optional[int]:
    """Best effort: GPUs per replica of a shape, used for multinode commands."""
    if not resource_shape:
        return None
    try:
        shapes = client.shapes.list_shapes(
            node_group=node_group_id, purpose="deployment"
        )
    except Exception:
        return None
    for shape in shapes:
        names = {shape.metadata.id_, shape.metadata.name, shape.spec.name}
        if resource_shape in names and shape.spec.accelerator_num:
            return int(shape.spec.accelerator_num)
    return None


def _warn_if_unofficial_image(name: str, service: LeptonDynamoServiceSpec, framework):
    container = _main_container(service)
    image = container.image if container else None
    if not image or framework not in DYNAMO_RUNTIME_IMAGES:
        return
    prefix = DYNAMO_RUNTIME_IMAGES[framework] + ":"
    tag = image[len(prefix) :] if image.startswith(prefix) else None
    if tag is None or tag not in SUPPORTED_DYNAMO_VERSIONS:
        console.print(
            f"[yellow]Warning:[/] service {name!r} uses image {image!r}. The server"
            f" only accepts the official runtime image for {framework}"
            f" ({DYNAMO_RUNTIME_IMAGES[framework]}) with a supported Dynamo version"
            f" tag ({', '.join(SUPPORTED_DYNAMO_VERSIONS)}); the request may be"
            " rejected."
        )


def _parse_int(value: Optional[str], flag: str) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        raise click.UsageError(f'"{flag}" expects an integer, got {value!r}.')


def _service_input_from_block(
    block: Dict[str, Any],
    client: APIClient,
    *,
    framework: Optional[str],
) -> DynamoServiceInput:
    node_groups = (
        _resolve_node_group_ids(client, block["node_group"])
        if block.get("node_group")
        else None
    )
    svc = DynamoServiceInput(
        name=block["key"],
        resource_shape=block.get("resource_shape"),
        node_groups=node_groups,
        replicas=_parse_int(block.get("replicas"), "--replicas"),
        node_count=_parse_int(block.get("node_count"), "--node-count"),
        image=block.get("image"),
        working_dir=block.get("working_dir"),
        command=block.get("command"),
        envs=list(block.get("env") or []),
        secrets=list(block.get("secret") or []),
        mounts=list(block.get("mount") or []),
        annotations=list(block.get("annotation") or []),
        labels=list(block.get("label") or []),
        shared_memory_size=_parse_int(
            block.get("shared_memory_size"), "--shared-memory-size"
        ),
        termination_grace_period_seconds=_parse_int(
            block.get("termination_grace_period"), "--termination-grace-period"
        ),
    )
    if svc.node_count and framework == "sglang":
        svc.gpu_count = _lookup_shape_gpu_count(
            client, node_groups[0] if node_groups else None, svc.resource_shape
        )
    return svc


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------


@click_group()
def dynamo():
    """
    Manage Dynamo graph deployments on DGX Cloud Lepton.

    A Dynamo deployment is a multi-service inference graph: a frontend service
    plus optional worker services (aggregated mode) or prefill/decode workers
    (disaggregated mode), each with its own resource shape, replicas, image,
    command, environment variables, and storage mounts.
    """
    pass


# ---------------------------------------------------------------------------
# list / get / status
# ---------------------------------------------------------------------------


def _print_dynamo_table(deployments: List[LeptonDynamoGraphDeployment]) -> None:
    table = Table(title="Dynamo Deployments", show_lines=True, show_header=True)
    table.add_column("Name")
    table.add_column("State")
    table.add_column("Framework")
    table.add_column("Mode")
    table.add_column("Ingress")
    table.add_column("Services (replicas x shape)")
    table.add_column("Node Groups")
    table.add_column("Created At")
    table.add_column("Created By")

    for dep in deployments:
        metadata = dep.metadata or Metadata()
        spec = dep.spec or LeptonDynamoGraphDeploymentUserSpec()
        status = dep.status
        services = spec.services or {}
        name_cell = make_name_id_cell(
            metadata.name or metadata.id_,
            metadata.id_ if metadata.id_ and metadata.id_ != metadata.name else None,
        )
        service_lines = [
            _service_summary_line(
                svc_name, services[svc_name], status.services if status else None
            )
            for svc_name in sort_service_names(list(services))
        ]
        table.add_row(
            name_cell,
            colorize_state(_state_text(status.state) if status else None),
            spec.backend_framework or "-",
            serving_mode_from_services(list(services)) if services else "-",
            "Enabled" if spec.ingress_enabled else "Disabled",
            "\n".join(service_lines) if service_lines else "-",
            ", ".join(_node_groups_of(spec)) or "-",
            format_timestamp_ms(metadata.created_at),
            metadata.created_by or "-",
        )

    if not deployments:
        console.print(
            "No Dynamo deployments found. Use `lep dynamo create` to create one."
        )
        return
    console.print(table)


@dynamo.command(name="list")
@click.option(
    "--name",
    "-n",
    multiple=True,
    help="Filter by name (case-insensitive substring). Can be repeated.",
)
@click.option(
    "--state",
    multiple=True,
    help=(
        "Filter by deployment state, e.g. Ready, 'Not Ready', Starting, Updating,"
        " Deleting. Case-insensitive; can be repeated."
    ),
)
@click.option(
    "--created-by",
    multiple=True,
    help="Filter by creator username. Can be repeated.",
)
def list_command(name, state, created_by):
    """
    Lists Dynamo deployments in the current workspace, newest first.
    """
    client = APIClient()
    deployments = client.dynamo.list_all()

    if name:
        needles = [n.lower() for n in name]
        deployments = [
            d
            for d in deployments
            if d.metadata
            and any(
                needle in (d.metadata.name or d.metadata.id_ or "").lower()
                for needle in needles
            )
        ]
    if state:
        wanted = {_normalize_token(s) for s in state}
        deployments = [
            d
            for d in deployments
            if d.status and _normalize_token(_state_text(d.status.state)) in wanted
        ]
    if created_by:
        wanted_users = set(created_by)
        deployments = [
            d
            for d in deployments
            if d.metadata and d.metadata.created_by in wanted_users
        ]

    deployments.sort(
        key=lambda d: (d.metadata.created_at or 0) if d.metadata else 0, reverse=True
    )
    _print_dynamo_table(deployments)


@dynamo.command()
@click.option("--name", "-n", help="The Dynamo deployment name.", required=True)
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
        "Optional local path to save the deployment spec JSON (reusable with"
        " `lep dynamo create -f`). Directory or full filename accepted. If a"
        " directory is provided, the file is saved as dynamo-spec-<name>.json."
    ),
    required=False,
)
def get(name, path):
    """
    Prints the full Dynamo deployment as JSON and optionally saves its spec.
    """
    client = APIClient()
    dep = client.dynamo.get(name)
    console.print(
        json.dumps(client.dynamo.safe_json(dep), indent=2),
        markup=False,
        highlight=False,
    )

    if path:
        spec_json = (
            dep.spec.model_dump_json(indent=2, exclude_none=True, by_alias=True)
            if dep.spec
            else "{}"
        )
        try:
            save_path = resolve_save_path(path, f"dynamo-spec-{name}.json")
        except PathResolutionError as e:
            console.print(f"[red]Failed to save spec: {e}[/]")
            sys.exit(1)
        try:
            with open(save_path, "w") as f:
                f.write(spec_json)
        except Exception as e:
            console.print(f"[red]Failed to save spec: {e}[/]")
            sys.exit(1)
        console.print(f"Dynamo deployment spec saved to [green]{save_path}[/].")


def _services_table(
    dep: LeptonDynamoGraphDeployment, infos: Optional[Dict[str, Any]]
) -> Table:
    table = Table(show_lines=False)
    table.add_column("Service")
    table.add_column("Type")
    table.add_column("Shape")
    table.add_column("Replicas (ready/desired)")
    table.add_column("Pods")
    table.add_column("Multinode")
    table.add_column("State")

    spec_services = (dep.spec.services if dep.spec else None) or {}
    status_services = (dep.status.services if dep.status else None) or {}
    for svc_name in _sorted_services(dep):
        service = spec_services[svc_name]
        info = (infos or {}).get(svc_name)
        status = status_services.get(svc_name)
        ready = (
            info.ready_replicas
            if info is not None and info.ready_replicas is not None
            else (status.ready_replicas if status else None)
        )
        desired = (
            info.desired_replicas
            if info is not None and info.desired_replicas is not None
            else (status.desired_replicas if status else service.min_replicas)
        )
        if info is not None and info.is_multinode:
            multinode = f"{info.node_count or '?'} nodes"
        elif service.multinode and service.multinode.node_count:
            multinode = f"{service.multinode.node_count} nodes"
        else:
            multinode = "-"
        table.add_row(
            svc_name,
            service.component_type or (info.component_type if info else None) or "-",
            service.resource_shape or "-",
            f"{ready if ready is not None else '-'}/{desired if desired is not None else '-'}",
            (
                str(info.total_pods)
                if info is not None and info.total_pods is not None
                else "-"
            ),
            multinode,
            colorize_state(_state_text(status.state) if status else None),
        )
    return table


def _replicas_table(rows: Iterable[Tuple[str, DynamoReplica]]) -> Tuple[Table, int]:
    table = Table(show_lines=False)
    table.add_column("Replica")
    table.add_column("Service")
    table.add_column("Status")
    table.add_column("Node")
    table.add_column("Created At")
    count = 0
    for svc_name, replica in rows:
        reason = _replica_reason(replica)
        node = replica.status.node if replica.status else None
        table.add_row(
            replica.metadata.id_ or replica.id_ or "-",
            svc_name,
            _colorize_readiness(reason),
            (node.name or node.id_ or "-") if node else "-",
            _fmt_ts(replica.metadata.created_at),
        )
        count += 1
    return table, count


def _collect_replicas(
    client: APIClient, name: str, services: Sequence[str]
) -> List[Tuple[str, DynamoReplica]]:
    rows: List[Tuple[str, DynamoReplica]] = []
    for svc_name in services:
        resp = client.dynamo.list_service_replicas(name, svc_name)
        for replica in resp.replicas:
            rows.append((svc_name, replica))
    return rows


@dynamo.command()
@click.option("--name", "-n", help="The Dynamo deployment name.", required=True)
@click.option(
    "--detail", "-d", is_flag=True, default=False, help="Also dump the full object."
)
def status(name, detail):
    """
    Shows the status of a Dynamo deployment: summary, services, health, and replicas.
    """
    client = APIClient()
    dep = client.dynamo.get(name)
    spec = dep.spec or LeptonDynamoGraphDeploymentUserSpec()
    metadata = dep.metadata or Metadata()
    st = dep.status
    state_text = _state_text(st.state) if st else None
    services = _sorted_services(dep)

    console.print(f"Time now:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    console.print(f"Created at:  {_fmt_ts(metadata.created_at)}")
    console.print(f"Created by:  {metadata.created_by or '-'}")
    if metadata.last_modified_at:
        console.print(
            f"Modified at: {_fmt_ts(metadata.last_modified_at)}"
            f" by {metadata.last_modified_by or '-'}"
        )
    console.print(f"State:       {colorize_state(state_text)}")
    console.print(
        f"Framework:   {spec.backend_framework or '-'} (Dynamo"
        f" {spec.dynamo_version or DYNAMO_VERSION})"
    )
    console.print(
        f"Mode:        {serving_mode_from_services(services) if services else '-'}"
    )
    ingress = "Enabled" if spec.ingress_enabled else "Disabled"
    if spec.ingress_timeout_seconds:
        ingress += f" (timeout {spec.ingress_timeout_seconds}s)"
    console.print(f"Ingress:     {ingress}")
    external = st.endpoint.external_endpoint if st and st.endpoint else None
    if external:
        if state_text == "Ready":
            console.print(f"Endpoint:    {external}")
        else:
            console.print(
                f"Endpoint:    {external} [bright_black](unavailable until Ready)[/]"
            )
    console.print(f"Node groups: {', '.join(_node_groups_of(spec)) or '-'}")
    console.print(f"Global envs: {_env_summary(spec.envs)}")

    console.print("\nServices:")
    infos = None
    try:
        infos = client.dynamo.list_services(name).services
    except (ClientError, ServerError) as e:
        console.print(f"[yellow]Live service status unavailable: {e}[/]")
    console.print(_services_table(dep, infos))

    try:
        health = client.dynamo.get_monitoring_status(name)
        console.print(
            f"Health:      {_colorize_health(health.overall_health)}"
            f" ({health.healthy_services or 0}/{health.total_services or 0} services"
            " healthy)"
        )
    except (ClientError, ServerError) as e:
        console.print(f"[yellow]Health status unavailable: {e}[/]")

    console.print("\nReplicas:")
    try:
        rows = _collect_replicas(client, name, services)
    except (ClientError, ServerError) as e:
        console.print(f"[yellow]Replica list unavailable: {e}[/]")
        rows = []
    table, count = _replicas_table(rows)
    if count:
        console.print(table)
        ready_count = sum(1 for _, r in rows if _replica_reason(r) == "Ready")
        console.print(f"[green]{ready_count}[/] out of {count} replicas ready.")
    else:
        console.print("No replicas found.")

    if detail:
        console.print(
            Pretty(dep.model_dump(mode="json", exclude_none=True, by_alias=True))
        )


# ---------------------------------------------------------------------------
# services / service / restart
# ---------------------------------------------------------------------------


@dynamo.command()
@click.option("--name", "-n", help="The Dynamo deployment name.", required=True)
def services(name):
    """
    Lists the services of a Dynamo deployment with their replica counts.
    """
    client = APIClient()
    dep = client.dynamo.get(name)
    infos = None
    try:
        infos = client.dynamo.list_services(name).services
    except (ClientError, ServerError) as e:
        console.print(f"[yellow]Live service status unavailable: {e}[/]")
    if not _sorted_services(dep):
        console.print(f"Dynamo deployment [yellow]{name}[/] has no services.")
        return
    console.print(_services_table(dep, infos))


@dynamo.command()
@click.option("--name", "-n", help="The Dynamo deployment name.", required=True)
@click.option("--service", "-s", help="The service name.", required=True)
@click.option(
    "--detail", "-d", is_flag=True, default=False, help="Also dump the raw response."
)
def service(name, service, detail):
    """
    Shows one service of a Dynamo deployment: spec, runtime status, and run command.
    """
    client = APIClient()
    svc = client.dynamo.get_service(name, service)
    spec = svc.spec or LeptonDynamoServiceSpec()
    st = svc.status
    container = _main_container(spec)

    console.print(f"Service:      {svc.name or service}")
    console.print(f"Type:         {svc.component_type or spec.component_type or '-'}")
    state_line = colorize_state(st.state if st and st.state else None)
    extras = []
    if st and st.phase:
        extras.append(f"phase: {st.phase}")
    if st and st.health:
        extras.append(f"health: {st.health}")
    if extras:
        state_line += f" ({', '.join(extras)})"
    console.print(f"State:        {state_line}")
    replicas = st.replicas if st else None
    console.print(
        "Replicas:     ready"
        f" {(replicas.ready if replicas else svc.ready_replicas) or 0} / desired"
        f" {(replicas.desired if replicas else svc.desired_replicas) or spec.min_replicas or 0} (running"
        f" {(replicas.running if replicas else svc.running_replicas) or 0}, pods"
        f" {(replicas.total_pods if replicas else svc.total_pods) or 0})"
    )
    console.print(f"Shape:        {svc.resource_shape or spec.resource_shape or '-'}")
    groups = (
        spec.affinity.allowed_dedicated_node_groups if spec.affinity else None
    ) or []
    console.print(f"Node groups:  {', '.join(groups) or '-'}")
    if svc.is_multinode or spec.multinode:
        node_count = svc.node_count or (
            spec.multinode.node_count if spec.multinode else None
        )
        console.print(f"Multinode:    {node_count or '?'} nodes")
    else:
        console.print("Multinode:    single node")
    console.print(f"Image:        {(container.image if container else None) or '-'}")
    console.print(
        f"Working dir:  {(container.working_dir if container else None) or '-'}"
    )
    command = command_display_string(container.command if container else None)
    console.print(f"Command:      {command or '-'}", markup=False, highlight=False)
    console.print(f"Envs:         {_env_summary(spec.envs)}")
    if spec.mounts:
        mounts = ", ".join(f"{m.from_} -> {m.mount_path}" for m in spec.mounts)
        console.print(f"Mounts:       {mounts}")
    if spec.extra_pod_metadata:
        if spec.extra_pod_metadata.labels:
            labels = ", ".join(
                f"{k}={v}" for k, v in spec.extra_pod_metadata.labels.items()
            )
            console.print(f"Labels:       {labels}")
        if spec.extra_pod_metadata.annotations:
            annotations = ", ".join(
                f"{k}={v}" for k, v in spec.extra_pod_metadata.annotations.items()
            )
            console.print(f"Annotations:  {annotations}")
    if st and st.uptime:
        console.print(f"Uptime:       {st.uptime}s")

    if st and st.conditions:
        table = Table(title="Conditions", show_lines=False)
        table.add_column("Type")
        table.add_column("Status")
        table.add_column("Reason")
        table.add_column("Message")
        for cond in st.conditions:
            table.add_row(
                cond.type_ or "-",
                cond.status or "-",
                cond.reason or "-",
                cond.message or "-",
            )
        console.print(table)
    if st and st.last_replica_error_events:
        table = Table(title="Recent replica errors", show_lines=False)
        table.add_column("Replica")
        table.add_column("Reason")
        table.add_column("Message")
        table.add_column("Node")
        table.add_column("Time")
        for event in st.last_replica_error_events:
            table.add_row(
                event.name or "-",
                f"[yellow]{event.reason or '-'}[/]",
                event.message or "-",
                event.node_name or "-",
                _fmt_ts(event.timestamp),
            )
        console.print(table)

    if detail:
        console.print(
            Pretty(svc.model_dump(mode="json", exclude_none=True, by_alias=True))
        )


@dynamo.command()
@click.option("--name", "-n", help="The Dynamo deployment name.", required=True)
@click.option("--service", "-s", help="The service to restart.", required=True)
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip the confirmation.")
def restart(name, service, yes):
    """
    Restarts a service by deleting all of its replicas (pods); the operator
    launches replacements.
    """
    client = APIClient()
    svc = client.dynamo.get_service(name, service)
    min_replicas = svc.min_replicas
    if min_replicas is None and svc.spec is not None:
        min_replicas = svc.spec.min_replicas
    if (min_replicas or 0) <= 0:
        console.print(
            f"[red]Service {service!r} has no replicas (min_replicas <= 0); nothing"
            " to restart.[/]"
        )
        sys.exit(1)
    phase = (svc.status.phase or svc.status.state or "") if svc.status else ""
    if "delet" in str(phase).lower():
        console.print(
            f"[red]Service {service!r} is being deleted; restart is disabled.[/]"
        )
        sys.exit(1)

    _confirm(f"Are you sure to restart the service {service!r} of {name!r}?", yes)
    resp = client.dynamo.restart_service(name, service)
    console.print(
        f"Restart request has been sent for service [green]{service}[/] of"
        f" [green]{name}[/]."
    )
    if resp.message:
        console.print(resp.message)
    if resp.deleted_pods:
        console.print("Deleted pods: " + ", ".join(resp.deleted_pods))


# ---------------------------------------------------------------------------
# replicas / log / remove-replica / remove
# ---------------------------------------------------------------------------


@dynamo.command()
@click.option("--name", "-n", help="The Dynamo deployment name.", required=True)
@click.option(
    "--service",
    "-s",
    default=None,
    help="Only list replicas of this service. Defaults to all services.",
)
@click.option(
    "--state",
    multiple=True,
    help=(
        "Filter by replica readiness status, e.g. Ready, InProgress, Failed,"
        " Terminated. Case-insensitive; can be repeated."
    ),
)
def replicas(name, service, state):
    """
    Lists the replicas (pods) of a Dynamo deployment, per service.
    """
    client = APIClient()
    dep = client.dynamo.get(name)
    services_ = _sorted_services(dep)
    if service:
        if services_ and service not in services_:
            console.print(
                f"[red]Service {service!r} not found in {name!r}. Available services:"
                f" {', '.join(services_)}[/]"
            )
            sys.exit(1)
        services_ = [service]
    rows = _collect_replicas(client, name, services_)
    if state:
        wanted = {_normalize_token(s) for s in state}
        rows = [
            (s, r) for s, r in rows if _normalize_token(_replica_reason(r)) in wanted
        ]
    table, count = _replicas_table(rows)
    if not count:
        console.print(f"No replicas found for [yellow]{name}[/].")
        return
    console.print(table)


def _pick_replica(
    client: APIClient, name: str, service: Optional[str]
) -> Tuple[str, str]:
    dep = client.dynamo.get(name)
    services_ = _sorted_services(dep)
    check(services_, f"Dynamo deployment [red]{name}[/] has no services.")
    if service is None:
        service = (
            DYNAMO_FRONTEND_SERVICE
            if DYNAMO_FRONTEND_SERVICE in services_
            else services_[0]
        )
    elif service not in services_:
        console.print(
            f"[red]Service {service!r} not found in {name!r}. Available services:"
            f" {', '.join(services_)}[/]"
        )
        sys.exit(1)
    resp = client.dynamo.list_service_replicas(name, service)
    check(
        len(resp.replicas) > 0,
        f"No replicas found for service [red]{service}[/] of [red]{name}[/].",
    )
    ordered = sorted(
        resp.replicas,
        key=lambda r: (_replica_reason(r) != "Ready", r.metadata.created_at or 0),
    )
    replica = ordered[0].metadata.id_ or ordered[0].id_ or ""
    return service, replica


@dynamo.command()
@click.option("--name", "-n", help="The Dynamo deployment name.", required=True)
@click.option(
    "--service",
    "-s",
    default=None,
    help=(
        "The service whose replica log to show. Defaults to `frontend` when"
        " --replica is not given."
    ),
)
@click.option(
    "--replica",
    "-r",
    default=None,
    help="The replica (pod) name. Defaults to the first ready replica of the service.",
)
@click.option(
    "--tail",
    type=click.IntRange(min=1),
    default=None,
    help="Number of most recent log lines to return (server default: 100).",
)
@click.option(
    "--timestamps",
    is_flag=True,
    default=False,
    help="Prefix each line with its timestamp.",
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
    default=None,
    help=(
        "Save the log to a local file instead of printing it. Directory or full"
        " filename accepted."
    ),
)
def log(name, service, replica, tail, timestamps, path):
    """
    Gets the current log of one replica of a Dynamo deployment.

    This returns a snapshot (the last N lines) rather than a stream. For
    historical, time-scoped logs use `lep log get --dynamo <name>`.
    """
    client = APIClient()
    if not replica:
        service, replica = _pick_replica(client, name, service)
        console.print(
            f"Replica not specified; selected replica [green]{replica}[/] of service"
            f" [green]{service}[/]."
        )
    resp = client.dynamo.get_replica_log(
        name, replica, service=service, tail=tail, timestamps=timestamps
    )
    text = resp.logs or ""
    if path:
        try:
            save_path = resolve_save_path(path, f"dynamo-log-{name}-{replica}.txt")
        except PathResolutionError as e:
            console.print(f"[red]Failed to save log: {e}[/]")
            sys.exit(1)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(text)
        console.print(f"Log saved to [green]{save_path}[/].")
        return
    if text:
        console.print(
            text, markup=False, highlight=False, end="" if text.endswith("\n") else "\n"
        )
    else:
        console.print("[yellow](empty log)[/]")
    console.print(
        "[bright_black]Snapshot only. Use `--tail N` for more lines or"
        f" `lep log get --dynamo {name} --replica {replica}` for historical logs.[/]"
    )


@dynamo.command(name="remove-replica")
@click.option("--name", "-n", help="The Dynamo deployment name.", required=True)
@click.option(
    "--replica", "-r", help="The replica (pod) name to delete.", required=True
)
@click.option(
    "--service",
    "-s",
    default=None,
    help="The service the replica belongs to (verified server side when given).",
)
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip the confirmation.")
def remove_replica(name, replica, service, yes):
    """
    Deletes one replica (pod). A new replica is launched to replace it, so
    capacity is briefly one replica short of the desired count.
    """
    client = APIClient()
    _confirm(
        f"The replica {replica!r} will immediately be deleted and a new replica will"
        " be launched. Continue?",
        yes,
    )
    resp = client.dynamo.delete_replica(name, replica, service=service)
    console.print(
        f"Replica [green]{resp.replica or replica}[/] of service"
        f" [green]{resp.service or service or '-'}[/] is being deleted."
    )
    if resp.message:
        console.print(resp.message)


@dynamo.command()
@click.option(
    "--name", "-n", help="The Dynamo deployment name to remove.", required=True
)
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip the confirmation.")
def remove(name, yes):
    """
    Removes a Dynamo deployment.
    """
    client = APIClient()
    _confirm(f"Are you sure to delete the Dynamo deployment {name!r}?", yes)
    client.dynamo.delete(name)
    console.print(f"Deletion request has been sent for [green]{name}[/].")


# ---------------------------------------------------------------------------
# history / metrics
# ---------------------------------------------------------------------------


@dynamo.command()
@click.option("--name", "-n", help="The Dynamo deployment name.", required=True)
def history(name):
    """
    Shows the recorded history (creation and updates) of a Dynamo deployment.
    """
    client = APIClient()
    items = client.dynamo.get_history(name)
    if not items:
        console.print(f"No history recorded for [yellow]{name}[/].")
        return
    table = Table(show_lines=False)
    table.add_column("Time")
    table.add_column("Operation")
    table.add_column("Description")
    for item in items:
        table.add_row(
            _fmt_ts(item.timestamp), item.operation or "-", item.description or "-"
        )
    console.print(table)


def _summarize_series(series: Any) -> List[Tuple[str, str, str, str, str, int, str]]:
    """Reduce ``[{metric, values}]`` to per-series latest/min/avg/max rows."""
    rows = []
    if not isinstance(series, list):
        return rows
    for entry in series:
        if not isinstance(entry, dict):
            continue
        metric = entry.get("metric") or {}
        values = []
        last_ts = None
        for point in entry.get("values") or []:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                continue
            ts, raw = point
            if raw is None:
                continue
            try:
                values.append(float(raw))
                last_ts = ts
            except (TypeError, ValueError):
                continue
        if not values:
            continue
        latest = values[-1]
        rows.append((
            str(metric.get("name") or "-"),
            str(metric.get("device") or "-"),
            f"{latest:.4g}",
            f"{min(values):.4g}",
            f"{sum(values) / len(values):.4g}",
            f"{max(values):.4g}",
            len(values),
            _fmt_ts(int(float(last_ts) * 1000)) if last_ts is not None else "-",
        ))
    return rows


@dynamo.command()
@click.option("--name", "-n", help="The Dynamo deployment name.", required=True)
@click.option(
    "--replica",
    "-r",
    default=None,
    help=(
        "Show replica-level metrics for this replica instead of deployment-level ones."
    ),
)
@click.option(
    "--metric",
    "-m",
    multiple=True,
    help=(
        "Metric name(s) to fetch. Defaults to the dashboard set:"
        f" {', '.join(DEPLOYMENT_METRICS)} at deployment level and"
        f" {', '.join(REPLICA_METRICS)} at replica level."
    ),
)
@click.option(
    "--window",
    type=click.Choice(METRIC_WINDOWS),
    default="1",
    show_default=True,
    help="Time window in hours (deployment-level metrics only).",
)
def metrics(name, replica, metric, window):
    """
    Prints a summary (latest, min, avg, max) of GPU and resource metrics.
    """
    client = APIClient()
    names = (
        list(metric)
        if metric
        else list(REPLICA_METRICS if replica else DEPLOYMENT_METRICS)
    )
    table = Table(
        title=f"Metrics for {name}"
        + (f" / {replica}" if replica else f" (last {window}h)"),
        show_lines=False,
    )
    for column in (
        "Metric",
        "Series",
        "Device",
        "Latest",
        "Min",
        "Avg",
        "Max",
        "Samples",
        "Last Seen",
    ):
        table.add_column(column)
    row_count = 0
    for metric_name in names:
        try:
            if replica:
                series = client.dynamo.get_replica_metric(name, replica, metric_name)
            else:
                series = client.dynamo.get_metric(name, metric_name, window=int(window))
        except ClientError as e:
            status_code = getattr(getattr(e, "response", None), "status_code", None)
            if status_code == 404:
                continue  # the dashboard hides panels whose metric is unavailable
            table.add_row(
                metric_name,
                "-",
                "-",
                f"[red]error {status_code}[/]",
                "-",
                "-",
                "-",
                "-",
                "-",
            )
            row_count += 1
            continue
        except ServerError:
            table.add_row(
                metric_name, "-", "-", "[yellow]unavailable[/]", "-", "-", "-", "-", "-"
            )
            row_count += 1
            continue
        rows = _summarize_series(series)
        if not rows:
            table.add_row(
                metric_name,
                "-",
                "-",
                "[bright_black]no data[/]",
                "-",
                "-",
                "-",
                "0",
                "-",
            )
            row_count += 1
            continue
        for series_name, device, latest, min_, avg, max_, samples, last_seen in rows:
            table.add_row(
                metric_name,
                series_name,
                device,
                latest,
                min_,
                avg,
                max_,
                str(samples),
                last_seen,
            )
            row_count += 1
    if not row_count:
        console.print(f"No metrics available for [yellow]{name}[/].")
        return
    console.print(table)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

_SERVICE_BLOCK_FLAGS = {
    "--resource-shape": "resource_shape",
    "--node-group": "node_group",
    "--replicas": "replicas",
    "--node-count": "node_count",
    "--image": "image",
    "--working-dir": "working_dir",
    "--command": "command",
    "--env": "env",
    "-e": "env",
    "--secret": "secret",
    "-s": "secret",
    "--mount": "mount",
    "--annotation": "annotation",
    "--label": "label",
    "--shared-memory-size": "shared_memory_size",
    "--termination-grace-period": "termination_grace_period",
}
_SERVICE_BLOCK_LIST_FIELDS = (
    "node_group",
    "env",
    "secret",
    "mount",
    "annotation",
    "label",
)

_SERVICE_BLOCK_HELP = """\
Service blocks (-svc/--service TYPE)
  Define services by repeating `-svc TYPE` followed by per-service flags. TYPE is
  one of: frontend, worker (aggregated mode), prefill-worker, decode-worker
  (disaggregated mode). Global options (--framework, --serving-mode, -e/-s for
  shared envs, ...) must come before the first -svc block; inside a block, -e/-s
  set per-service envs. Example:

    lep dynamo create -n my-llm --framework vllm \\
      -svc frontend --resource-shape cpu.small --node-group my-ng \\
      -svc worker --resource-shape gpu.h100-80gb --replicas 2 \\
        -e MODEL=Qwen/Qwen3-0.6B -s HF_TOKEN

  Rules (same as the dashboard):
    - frontend is required; workers inherit the frontend's node group.
    - vLLM only supports aggregated mode.
    - --node-count (multinode) is only available for SGLang workers.
    - image, working dir and command default to the official Dynamo runtime for
      the chosen framework/version; override them only if you know the server
      accepts the value.
    - prefill/decode workers get the label lepton.ai/dynamo-worker-role.

  Per-service flags:
    --resource-shape TEXT          REQUIRED for new services.
    --node-group TEXT              Dedicated node group (name or id). Frontend only;
                                   workers inherit it.
    --replicas INTEGER             Replica count (default 1, >= 1).
    --node-count INTEGER           Multinode node count (>= 2, SGLang workers only).
    --image TEXT                   Container image (default: official runtime image).
    --working-dir TEXT             Container working directory.
    --command TEXT                 Run command, executed via `/bin/sh -c`.
    --env, -e NAME=VALUE           Repeatable. Per-service environment variables.
    --secret, -s NAME[=SECRET]     Repeatable. Secret injected as env var NAME.
    --mount FROM_PATH:MOUNT_PATH:VOLUME
                                   Repeatable. VOLUME is `node-local` or
                                   `node-<type>:<storage_name>` (e.g. node-nfs:my-nfs).
    --annotation KEY=VALUE         Repeatable. Pod annotations.
    --label KEY=VALUE              Repeatable. Pod labels.
    --shared-memory-size INTEGER   Shared memory (/dev/shm) in MiB.
    --termination-grace-period INTEGER
                                   Pod termination grace period in seconds."""

ServiceBlockCommand = make_block_option_command(
    markers=("-svc", "--service"),
    flags=_SERVICE_BLOCK_FLAGS,
    list_fields=_SERVICE_BLOCK_LIST_FIELDS,
    param_name="service_blocks",
    help_text=_SERVICE_BLOCK_HELP,
)

_UPDATE_SERVICE_BLOCK_HELP = """\
Service blocks (-svc/--service NAME)
  Update or add services by repeating `-svc NAME` followed by per-service flags.
  Existing services keep every value you do not mention. A NAME that does not
  exist yet is added (it requires --resource-shape; the node group is inherited
  from the frontend). Example:

    lep dynamo update -n my-llm -svc worker --replicas 4 --command "python3 -m dynamo.vllm --model Qwen/Qwen3-8B"
    lep dynamo update -n my-llm -svc worker --remove

  Per-service flags: the same as `lep dynamo create` (--resource-shape,
  --node-group (frontend only), --replicas, --node-count (only if the service is
  already multinode), --image, --working-dir, --command, -e/--env, -s/--secret,
  --mount, --annotation, --label, --shared-memory-size,
  --termination-grace-period) plus:
    --remove                       Delete this service from the deployment.
    --clear-working-dir            Reset the working dir (frontend: /workspace,
                                   workers: image default)."""

UpdateServiceBlockCommand = make_block_option_command(
    markers=("-svc", "--service"),
    flags={
        **_SERVICE_BLOCK_FLAGS,
        "--remove": "remove",
        "--clear-working-dir": "clear_working_dir",
    },
    list_fields=_SERVICE_BLOCK_LIST_FIELDS,
    bool_flags=("remove", "clear_working_dir"),
    param_name="service_blocks",
    help_text=_UPDATE_SERVICE_BLOCK_HELP,
)


@dynamo.command(cls=ServiceBlockCommand)
@click.option(
    "--name", "-n", type=str, help="Name of the Dynamo deployment.", required=True
)
@click.option(
    "--file",
    "-f",
    type=click.Path(
        exists=False, file_okay=True, dir_okay=False, readable=True, resolve_path=True
    ),
    help=(
        "Load the deployment spec from this JSON file (as written by `lep dynamo get"
        " -p`) before applying CLI overrides."
    ),
    required=False,
)
@click.option(
    "--framework",
    type=click.Choice(DYNAMO_FRAMEWORKS),
    default=None,
    help="Backend framework. Default: vllm (or the value in --file).",
)
@click.option(
    "--serving-mode",
    type=click.Choice(DYNAMO_SERVING_MODES),
    default=None,
    help=(
        "aggregated (frontend + worker) or disaggregated (frontend + prefill-worker +"
        " decode-worker). Default: aggregated (or derived from --file)."
    ),
)
@click.option(
    "--dynamo-version",
    type=str,
    default=None,
    help=(
        "Dynamo version; drives image tags and default commands. Default:"
        f" {DYNAMO_VERSION}."
    ),
)
@click.option(
    "--ingress-enabled/--no-ingress",
    "ingress_enabled",
    default=None,
    help="Create an ingress for the frontend service. Default: enabled.",
)
@click.option(
    "--ingress-timeout",
    type=int,
    default=None,
    help="Ingress request timeout in seconds (300-3600; server default 300).",
)
@click.option(
    "--display-name", type=str, default=None, help="Human-friendly display name."
)
@click.option(
    "--env",
    "-e",
    multiple=True,
    help="Shared environment variables for all services, as `NAME=VALUE`. Repeatable.",
)
@click.option(
    "--secret",
    "-s",
    multiple=True,
    help=(
        "Shared secrets for all services, as `NAME=SECRET_NAME` (or just"
        " `SECRET_NAME`). Repeatable."
    ),
)
@click.option(
    "--image-pull-secrets",
    type=str,
    multiple=True,
    help="Secrets to use for pulling images, applied to every service. Repeatable.",
)
@click.option(
    "--visibility",
    type=click.Choice(["public", "private"]),
    default=None,
    help=(
        "Visibility of the deployment. Private deployments are only visible to the"
        " creator and admins."
    ),
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print the request payload instead of creating the deployment.",
)
def create(
    name,
    file,
    framework,
    serving_mode,
    dynamo_version,
    ingress_enabled,
    ingress_timeout,
    display_name,
    env,
    secret,
    image_pull_secrets,
    visibility,
    dry_run,
    service_blocks,
):
    """
    Creates a Dynamo deployment from CLI flags and/or a spec file.

    The frontend service is required; add workers with additional -svc blocks.
    Run `lep dynamo create --help` for the per-service flags and rules.
    """
    validate_dynamo_name(name)
    client = APIClient()

    base = _load_user_spec_file(file) if file else None
    effective_framework = (
        framework or (base.backend_framework if base else None) or "vllm"
    )
    inputs = [
        _service_input_from_block(block, client, framework=effective_framework)
        for block in service_blocks
    ]

    spec = build_dynamo_spec(
        services=inputs,
        framework=framework,
        serving_mode=serving_mode,
        dynamo_version=dynamo_version,
        ingress_enabled=ingress_enabled,
        ingress_timeout_seconds=ingress_timeout,
        display_name=display_name,
        envs=env,
        secrets=secret,
        image_pull_secrets=image_pull_secrets or None,
        base=base,
    )
    for svc_name, svc_spec in (spec.services or {}).items():
        _warn_if_unofficial_image(svc_name, svc_spec, spec.backend_framework)

    metadata_kwargs: Dict[str, Any] = {"name": name}
    if visibility:
        metadata_kwargs["visibility"] = LeptonVisibility(visibility)
    dep = LeptonDynamoGraphDeployment(metadata=Metadata(**metadata_kwargs), spec=spec)

    if dry_run:
        console.print(
            json.dumps(client.dynamo.safe_json(dep), indent=2),
            markup=False,
            highlight=False,
        )
        return

    created = client.dynamo.create(dep)
    created_name = (created.metadata.name if created.metadata else None) or name
    console.print(f"Dynamo deployment [green]{created_name}[/] created successfully.")
    console.print(
        f"Use `lep dynamo status -n {created_name}` to check its status, or"
        f" `lep dynamo log -n {created_name}` to read replica logs."
    )


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def _load_patch_file(path: str) -> Dict[str, Any]:
    payload = _load_json_file(path, "merge patch")
    if not isinstance(payload, dict):
        console.print(f"[red]The merge patch in {path} must be a JSON object.[/]")
        sys.exit(1)
    if "spec" not in payload:
        payload = {"spec": payload}
    return payload


@dynamo.command(cls=UpdateServiceBlockCommand)
@click.option(
    "--name", "-n", help="The Dynamo deployment name to update.", required=True
)
@click.option("--display-name", type=str, default=None, help="New display name.")
@click.option(
    "--ingress-enabled/--no-ingress",
    "ingress_enabled",
    default=None,
    help="Enable or disable the frontend ingress.",
)
@click.option(
    "--ingress-timeout",
    type=int,
    default=None,
    help="Ingress request timeout in seconds (300-3600).",
)
@click.option(
    "--env",
    "-e",
    multiple=True,
    help=(
        "Replace the shared environment variables (`NAME=VALUE`). Repeatable; the"
        " full list is replaced, not merged."
    ),
)
@click.option(
    "--secret",
    "-s",
    multiple=True,
    help=(
        "Replace the shared secrets (`NAME=SECRET_NAME`). Repeatable; used together"
        " with --env."
    ),
)
@click.option(
    "--file",
    "-f",
    type=click.Path(
        exists=False, file_okay=True, dir_okay=False, readable=True, resolve_path=True
    ),
    default=None,
    help=(
        'A raw RFC 7396 merge patch JSON ({"spec": {...}}) applied on top of the'
        " flag-derived patch. Use it for fields the flags do not cover."
    ),
)
@click.option(
    "--dryrun",
    "--dry-run",
    "dryrun",
    is_flag=True,
    default=False,
    help=(
        "Ask the server to validate the patch without persisting it, and print the"
        " patch."
    ),
)
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip the confirmation.")
def update(
    name,
    display_name,
    ingress_enabled,
    ingress_timeout,
    env,
    secret,
    file,
    dryrun,
    yes,
    service_blocks,
):
    """
    Updates a Dynamo deployment with a JSON Merge Patch built from the given
    flags. Only the fields you mention change; service changes may restart
    replicas and therefore ask for confirmation.
    """
    client = APIClient()
    current = client.dynamo.get(name)
    if current.spec is None:
        console.print(f"[red]Dynamo deployment {name!r} has no spec to update.[/]")
        sys.exit(1)
    original = current.spec
    desired = original.model_copy(deep=True)
    desired.services = dict(desired.services or {})
    framework = desired.backend_framework or "vllm"
    serving_mode = serving_mode_from_services(list(desired.services))

    if display_name is not None:
        desired.display_name = display_name
    if ingress_enabled is not None:
        desired.ingress_enabled = ingress_enabled
    if ingress_timeout is not None:
        desired.ingress_timeout_seconds = validate_ingress_timeout(ingress_timeout)
    if env or secret:
        desired.envs = make_env_vars_from_strings(list(env), list(secret))

    for block in service_blocks:
        svc_name = block["key"]
        existing = desired.services.get(svc_name)
        if block.get("remove"):
            if svc_name == DYNAMO_FRONTEND_SERVICE:
                raise ValueError("The frontend service cannot be removed.")
            if existing is None:
                raise ValueError(
                    f"Service {svc_name!r} does not exist in {name!r}; nothing to"
                    " remove."
                )
            del desired.services[svc_name]
            continue

        svc_input = _service_input_from_block(block, client, framework=framework)
        if existing is not None:
            if svc_input.node_count is not None and existing.multinode is None:
                raise ValueError(
                    f"service {svc_name}: cannot add multinode configuration to"
                    " existing service"
                )
            if (
                svc_input.node_groups is not None
                and svc_name != DYNAMO_FRONTEND_SERVICE
            ):
                raise ValueError(
                    "Worker node groups are automatically synchronized with the"
                    " frontend service; change the node group on the frontend instead."
                )
            new_spec = build_service_spec(
                svc_input,
                framework=framework,
                serving_mode=serving_mode,
                dynamo_version=desired.dynamo_version,
                frontend_node_groups=None,
                base=existing,
                fill_defaults=False,
            )
            if block.get("clear_working_dir"):
                container = _main_container(new_spec)
                if container is not None:
                    container.working_dir = (
                        "/workspace" if svc_name == DYNAMO_FRONTEND_SERVICE else None
                    )
        else:
            if svc_name not in DYNAMO_SERVICE_NAMES:
                raise ValueError(
                    f"Unknown Dynamo service {svc_name!r}. Expected one of:"
                    f" {', '.join(DYNAMO_SERVICE_NAMES)}."
                )
            new_spec = build_service_spec(
                svc_input,
                framework=framework,
                serving_mode=serving_mode,
                dynamo_version=desired.dynamo_version,
                frontend_node_groups=frontend_node_groups_of(desired),
                base=None,
            )
        desired.services[svc_name] = new_spec

    # Workers always follow the frontend node group (dashboard rule).
    frontend_groups = frontend_node_groups_of(desired)
    if frontend_groups:
        for svc_name, svc_spec in desired.services.items():
            if svc_name == DYNAMO_FRONTEND_SERVICE:
                continue
            if svc_spec.affinity is None:
                continue
            if svc_spec.affinity.allowed_dedicated_node_groups != list(frontend_groups):
                svc_spec.affinity.allowed_dedicated_node_groups = list(frontend_groups)

    spec_patch = build_merge_patch(spec_to_dict(original), spec_to_dict(desired))
    patch: Dict[str, Any] = {"spec": spec_patch} if spec_patch else {}
    if file:
        patch = deep_merge_patch(patch, _load_patch_file(file))

    if not patch.get("spec"):
        console.print("No changes detected.")
        return

    if dryrun:
        console.print("Merge patch:")
        console.print(json.dumps(patch, indent=2), markup=False, highlight=False)
    elif "services" in patch["spec"]:
        _confirm(
            "This update changes services and may restart running replicas of"
            f" {name!r}. Continue?",
            yes,
        )

    result = client.dynamo.update(name, patch, dryrun=dryrun)
    if dryrun:
        console.print(
            "[green]The server validated the patch (dry run; nothing was persisted).[/]"
        )
        preview = apply_merge_patch(spec_to_dict(original), patch.get("spec", {}))
        console.print(Pretty(preview))
        return
    result_name = (result.metadata.name if result.metadata else None) or name
    console.print(f"Dynamo deployment [green]{result_name}[/] updated successfully.")


def add_command(cli_group):
    cli_group.add_command(dynamo)
