import re

import click

from rich.table import Table

from .util import (
    console,
    click_group,
    format_timestamp_ms,
    get_client,
    make_name_id_cell,
    resolve_node_groups,
)
from ..api.v2.client import APIClient
from ..api.v2.types.dedicated_node_group import (
    Volume,
    VolumeCreationMode,
    VolumeFrom,
)
from ..api.v2.types.storage_data_source import (
    DataSourcePermissions,
    ObjectStorageConfig,
    ObjectStorageProviderConfig,
    StorageDataSourceSpec,
)
from ..api.v2.types.storage_permission import StoragePermission


@click_group()
def node():
    """
    Manage nodes on the DGX Cloud Lepton.
    """
    pass


def _is_node_usable(node):
    """A node is usable when it is ready, healthy, and schedulable."""
    status = (node.status.status if node.status else None) or []
    spec = getattr(node, "spec", None)
    return bool(spec) and (
        not getattr(spec, "unschedulable", True)
        and "Ready" in status
        and "Unhealthy" not in status
    )


def _node_group_type(node_group):
    """Render whether a node group is Lepton-managed or customer BYOC."""
    mode = getattr(node_group.spec, "node_mode", None)
    if mode == "lepton-node":
        return "[cyan]Lepton[/cyan]"
    if mode == "customer-node":
        return "[magenta]BYOC[/magenta]"
    return "[dim]-[/dim]"


def _get_node_group_stats(nodes):
    """Aggregate node counts and resource capacity across a node group.

    'avail' for GPU counts only idle GPUs on usable (ready/healthy/schedulable)
    nodes, so GPUs sitting on unhealthy or NotReady nodes are not reported as
    available capacity.
    """
    stats = {
        "healthy": 0,
        "error": 0,
        "total": len(nodes),
        "gpu_avail": 0.0,
        "gpu_used": 0.0,
        "gpu_total": 0.0,
        "cpu_used": 0.0,
        "cpu_total": 0.0,
        "mem_used": 0,
        "mem_total": 0,
        "disk_used": 0,
        "disk_total": 0,
    }
    for node in nodes:
        usable = _is_node_usable(node)
        stats["healthy" if usable else "error"] += 1

        resource = node.spec.resource if node.spec else None
        if not resource:
            continue
        if resource.gpu:
            total = resource.gpu.total or 0
            used = resource.gpu.allocated or 0
            stats["gpu_total"] += total
            stats["gpu_used"] += used
            if usable:
                stats["gpu_avail"] += max(0, total - used)
        if resource.cpu:
            stats["cpu_used"] += resource.cpu.allocated or 0
            stats["cpu_total"] += resource.cpu.total or 0
        if resource.memory:
            stats["mem_used"] += resource.memory.allocated or 0
            stats["mem_total"] += resource.memory.total or 0
        if resource.disk:
            stats["disk_used"] += resource.disk.used_bytes or 0
            stats["disk_total"] += resource.disk.total_bytes or 0
    return stats


def _colorize_status(status):
    """Colorize node status for better visualization"""
    if status == "Healthy":
        return f"[green]{status}[/green]"
    elif status == "Unhealthy":
        return f"[red]{status}[/red]"
    elif status == "Ready":
        return f"[green]{status}[/green]"
    else:  # NotReady or other statuses
        return f"[yellow]{status}[/yellow]"


def _format_shape_entry(shape):
    """Format a single Shape into two parts: (shape cell text, detailed cell text).

    Shapes column: two lines (name, colored availability tags)
    Detailed column: single line colored resource spec
    """
    spec = getattr(shape, "spec", None)
    meta = getattr(shape, "metadata", None)

    # Name preference: spec.name -> metadata.name -> metadata.id_
    name = (
        (getattr(spec, "name", None) if spec else None)
        or (getattr(meta, "name", None) if meta else None)
        or (getattr(meta, "id_", None) if meta else None)
        or "(unnamed)"
    )

    listable = set((getattr(spec, "listable_in", None) or [])) if spec else set()
    listable_lower = {str(x).lower() for x in listable}

    # Build availability tags
    pod_tag = "[green]pod[/green]" if "pod" in listable_lower else "[dim]pod[/dim]"
    endpoint_tag = (
        "[cyan]endpoint[/cyan]"
        if "deployment" in listable_lower
        else "[dim]endpoint[/dim]"
    )
    job_tag = "[magenta]job[/magenta]" if "job" in listable_lower else "[dim]job[/dim]"

    shape_cell_lines = [f"[bold]{name}[/bold]", f"{pod_tag}  {endpoint_tag}  {job_tag}"]

    # Detailed column with more colors
    cpu = getattr(spec, "cpu", None)
    mem = getattr(spec, "memory_in_mb", None)
    eph = getattr(spec, "ephemeral_storage_in_gb", None)
    acc_type = getattr(spec, "accelerator_type", None)
    acc_num = getattr(spec, "accelerator_num", None)
    acc_frac = getattr(spec, "accelerator_fraction", None)
    acc_mem = getattr(spec, "accelerator_memory_in_mb", None)

    # details: two lines -> line1: cpu + acc, line2: others (mem/eph/price)
    cpu_acc_parts = []
    if cpu is not None:
        cpu_acc_parts.append(f"cpu x [cyan]{int(cpu)}[/cyan]")

    acc_parts = []
    if acc_type:
        acc_parts.append(f"[yellow]{acc_type}[/yellow]")
    if acc_num is not None:
        acc_parts.append(f"x{int(acc_num)}")
    elif acc_frac is not None:
        acc_parts.append(f"fraction={acc_frac}")
    if acc_mem is not None:
        acc_parts.append(f"{acc_mem}MB")
    if acc_parts:
        cpu_acc_parts.append("acc: " + " ".join(acc_parts))

    other_parts = []
    if mem is not None:
        other_parts.append(f"[dim]mem={mem}MB[/dim]")
    if eph is not None:
        other_parts.append(f"[dim]ephemeral storage={eph}GB[/dim]")

    top_line = ", ".join(cpu_acc_parts)
    bottom_line = ", ".join(other_parts)
    detail_text = "\n".join([top_line, bottom_line])
    return "\n".join(shape_cell_lines), detail_text


@node.command(name="list")
@click.option(
    "--detail",
    "-d",
    is_flag=True,
    hidden=True,
    help="(removed) per-node detail moved to 'lep node list-nodes'.",
)
@click.option(
    "--node-group",
    "-ng",
    help=(
        "Show only node groups whose IDs or names match. Can use partial name/ID"
        " (e.g., 'h100' will match any name/ID containing 'h100'). Can specify"
        " multiple values."
    ),
    type=str,
    required=False,
    multiple=True,
)
def list_command(detail=False, node_group=None):
    """
    List node groups in the current workspace with a capacity summary.

    For each node group this shows node health (healthy/error/total), whether it
    is Lepton-managed or customer BYOC, and the aggregated GPU/CPU/memory/disk
    usage. For per-node detail, use 'lep node list-nodes <node-group>'.
    """
    if detail:
        console.print(
            "[yellow]Note:[/yellow] '-d/--detail' has been removed. For per-node"
            " detail, use [bold]lep node list-nodes <node-group>[/bold].\n"
        )

    client = get_client()

    if node_group:
        filtered_node_groups = resolve_node_groups(node_group, is_exact_match=False)
    else:
        filtered_node_groups = client.nodegroup.list_all()

    table = Table(title="Node Groups", show_lines=True)
    table.add_column("Node Group")
    table.add_column("Type")
    table.add_column("Nodes\n[dim](healthy / error / total)[/dim]")
    table.add_column("GPU\n[dim](avail · used/total)[/dim]")
    table.add_column("CPU\n[dim](used / total)[/dim]")
    table.add_column("Memory\n[dim](used / total)[/dim]")
    table.add_column("Disk\n[dim](used / total)[/dim]")

    nodes_results = []
    if filtered_node_groups:
        results_or_errors = client.nodegroup.batch_fetch_nodes(
            filtered_node_groups,
            concurrency=min(8, len(filtered_node_groups)),
            return_exceptions=True,
        )

        for idx, item in enumerate(results_or_errors):
            if isinstance(item, Exception):
                ng = filtered_node_groups[idx]
                name = getattr(getattr(ng, "metadata", None), "name", "unknown")
                id_ = getattr(getattr(ng, "metadata", None), "id_", "-")
                console.print(
                    f"[dim]Warning:[/dim] Failed to fetch node list for {name} ({id_}):"
                    f" {item}"
                )
                nodes_results.append([])
            else:
                nodes_results.append(item)

    for idx, ng in enumerate(filtered_node_groups):
        nodes = nodes_results[idx] if idx < len(nodes_results) else []
        stats = _get_node_group_stats(nodes)

        name_id = make_name_id_cell(ng.metadata.name, ng.metadata.id_)
        error_str = f"[red]{stats['error']}[/red]" if stats["error"] else "[dim]0[/dim]"
        health = f"[green]{stats['healthy']}[/green] / {error_str} / {stats['total']}"
        dim = "[dim]-[/dim]"
        avail_color = "green" if stats["gpu_avail"] > 0 else "dim"
        gpu_cell = (
            f"[{avail_color}]{_trim_num(stats['gpu_avail'])} avail[/{avail_color}]"
            f" · {_format_used_total(stats['gpu_used'], stats['gpu_total'])} used"
            if stats["gpu_total"]
            else dim
        )
        cpu_cell = (
            f"{_format_used_total(stats['cpu_used'], stats['cpu_total'])} cores"
            if stats["cpu_total"]
            else dim
        )
        mem_cell = (
            f"{_format_bytes(stats['mem_used'] * 1024 * 1024)} /"
            f" {_format_bytes(stats['mem_total'] * 1024 * 1024)}"
            if stats["mem_total"]
            else dim
        )
        disk_cell = (
            f"{_format_bytes(stats['disk_used'])} /"
            f" {_format_bytes(stats['disk_total'])}"
            if stats["disk_total"]
            else dim
        )

        table.add_row(
            name_id,
            _node_group_type(ng),
            health,
            gpu_cell,
            cpu_cell,
            mem_cell,
            disk_cell,
        )

    console.print(table)

    console.print(
        "[dim]Note:[/dim] GPU 'avail' counts only idle GPUs on healthy, ready,"
        " schedulable nodes. CPU/memory/disk are summed across the node group.\n"
    )


def _trim_num(value):
    """Render a number without a trailing '.0'; return '?' when missing."""
    if value is None:
        return "?"
    value = float(value)
    return str(int(value)) if value.is_integer() else f"{value:.1f}"


def _format_used_total(allocated, total):
    """Format an 'allocated/total' pair."""
    return f"{_trim_num(allocated)}/{_trim_num(total)}"


def _format_bytes(num):
    """Render a byte count in binary units (GiB/TiB...)."""
    if num is None:
        return "?"
    value = float(num)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
        if value < 1024 or unit == "PiB":
            return f"{value:.1f} {unit}"
        value /= 1024


def _format_gpu_cell(gpu, usable=True):
    """GPU column: product on line 1, avail and used/total on line 2.

    'avail' mirrors 'lep node list': idle GPUs only count as available when the
    node is usable (ready/healthy/schedulable); on an unusable node they are not
    reported as available capacity, so per-node and aggregate views agree.
    """
    if not gpu or gpu.total is None:
        return "[dim]-[/dim]"
    product = gpu.product or "GPU"
    allocated = gpu.allocated or 0
    avail = max(0, gpu.total - allocated) if usable else 0
    avail_color = "green" if avail > 0 else "dim"
    return (
        f"{product}\n[{avail_color}]{_trim_num(avail)} avail[/{avail_color}]"
        f" · {_format_used_total(allocated, gpu.total)} used"
    )


def _format_cpu_cell(cpu):
    if not cpu or cpu.total is None:
        return "[dim]-[/dim]"
    type_ = cpu.type_ or "cpu"
    return f"{type_}\n{_format_used_total(cpu.allocated, cpu.total)} cores"


def _format_memory_cell(memory):
    # memory allocated/total are reported in MiB.
    if not memory or memory.total is None:
        return "[dim]-[/dim]"
    used = _format_bytes((memory.allocated or 0) * 1024 * 1024)
    total = _format_bytes(memory.total * 1024 * 1024)
    return f"{used} / {total}"


def _format_disk_cell(disk):
    if not disk or disk.total_bytes is None:
        return "[dim]-[/dim]"
    used = _format_bytes(disk.used_bytes or 0)
    total = _format_bytes(disk.total_bytes)
    return f"{used} / {total}"


@node.command(name="list-nodes")
@click.argument("name", type=str)
def list_nodes_command(name):
    """
    List the nodes under a node group with per-node resource detail.

    NAME is the node group name or ID (partial match supported, e.g. 'h100').
    For each node it shows the node ID, provider/region, status, GPU
    availability, and the used/total split for GPU, CPU, memory, and disk.
    """
    node_groups = resolve_node_groups([name], is_exact_match=False)
    if not node_groups:
        return

    client = get_client()

    for node_group in node_groups:
        ng_name = node_group.metadata.name
        ng_id = node_group.metadata.id_

        try:
            nodes = client.nodegroup.list_nodes(node_group)
        except Exception as e:
            console.print(
                f"[red]Failed to fetch nodes for {ng_name} ({ng_id}):[/red] {e}"
            )
            continue

        table = Table(title=f"Nodes in {ng_name} ({ng_id})", show_lines=True)
        table.add_column("Node ID")
        table.add_column("Provider / Region")
        table.add_column("Status")
        table.add_column("GPU\n[dim](avail · used/total)[/dim]")
        table.add_column("CPU\n[dim](used / total)[/dim]")
        table.add_column("Memory\n[dim](used / total)[/dim]")
        table.add_column("Disk\n[dim](used / total)[/dim]")

        if not nodes:
            console.print(
                f"[yellow]No nodes found in node group {ng_name} ({ng_id}).[/yellow]"
            )
            continue

        for node in nodes:
            spec = node.spec
            resource = spec.resource if spec else None
            provider = (getattr(spec, "provider", None) if spec else None) or "-"
            region = (getattr(spec, "provider_region", None) if spec else None) or "-"
            statuses = (node.status.status if node.status else None) or []
            status_cell = ", ".join(_colorize_status(s) for s in statuses) or "-"

            table.add_row(
                make_name_id_cell(node.metadata.id_, None),
                f"{provider} / {region}",
                status_cell,
                _format_gpu_cell(
                    resource.gpu if resource else None,
                    usable=_is_node_usable(node),
                ),
                _format_cpu_cell(resource.cpu if resource else None),
                _format_memory_cell(resource.memory if resource else None),
                _format_disk_cell(resource.disk if resource else None),
            )

        console.print(table)


def _colorize_reservation_phase(phase):
    """Colorize a reservation phase for visualization.

    Mirrors the backend phase semantics: 'Reserved' is the usable end state,
    'Reserving'/'WaitingEffective' are in-progress, 'PendingApproval' is waiting
    on an admin, and 'Rejected'/'Expired' are dead.
    """
    text = (getattr(phase, "value", phase) if phase is not None else None) or "-"
    if text == "Reserved":
        return f"[green]{text}[/green]"
    if text in ("Reserving", "WaitingEffective"):
        return f"[cyan]{text}[/cyan]"
    if text == "PendingApproval":
        return f"[yellow]{text}[/yellow]"
    if text in ("Rejected", "Expired"):
        return f"[red]{text}[/red]"
    return f"[dim]{text}[/dim]"


def _format_reservation_gpu_cell(reserved_nodes, node_gpu_by_id):
    """Aggregate GPU used/total across a reservation's reserved nodes.

    The reservation payload carries no GPU data, so we cross-reference the
    reserved node IDs against the node group's node list (node_gpu_by_id maps a
    node id to its NodeResourceGPU). 'avail' is the idle GPU on those nodes.
    """
    used = 0.0
    total = 0.0
    products = set()
    matched = 0
    for node_id in reserved_nodes or []:
        gpu = node_gpu_by_id.get(node_id)
        if not gpu or gpu.total is None:
            continue
        matched += 1
        total += gpu.total or 0
        used += gpu.allocated or 0
        if gpu.product:
            products.add(gpu.product)
    if matched == 0:
        return "[dim]-[/dim]"
    product = products.pop() if len(products) == 1 else "GPU"
    avail = total - used
    avail_color = "green" if avail > 0 else "dim"
    return (
        f"{product}\n[{avail_color}]{_trim_num(avail)} avail[/{avail_color}]"
        f" · {_format_used_total(used, total)} used"
    )


def _format_reservation_row(reservation, node_gpu_by_id):
    """Build a single 'lep node list-reservations' table row from a NodeReservation."""
    meta = reservation.metadata
    spec = reservation.spec
    status = reservation.status

    # Reservation: display name on metadata.name (spec.display_name as fallback) / id.
    display_name = meta.name or (getattr(spec, "display_name", None) if spec else None)
    name_id = make_name_id_cell(display_name, meta.id_)

    status_cell = _colorize_reservation_phase(status.phase if status else None)

    # Nodes: desired / approved / reserved, with reserved node ids listed below.
    desired = spec.desired_nodes if spec else None
    approved = spec.approved_nodes if spec else None
    reserved = status.reserved_count if status else 0
    reserved_nodes = (status.reserved_nodes if status else None) or []
    desired_str = _trim_num(desired) if desired is not None else "[dim]-[/dim]"
    approved_str = _trim_num(approved) if approved is not None else "[dim]-[/dim]"
    reserved_color = "green" if reserved else "dim"
    nodes_lines = [
        f"{desired_str} / {approved_str} /"
        f" [{reserved_color}]{_trim_num(reserved)}[/{reserved_color}]"
    ]
    for node_id in reserved_nodes:
        nodes_lines.append(f"[dim]{node_id}[/dim]")
    nodes_cell = "\n".join(nodes_lines)

    gpu_cell = _format_reservation_gpu_cell(reserved_nodes, node_gpu_by_id)

    users = (spec.users if spec else None) or []
    users_cell = "\n".join(users) if users else "[dim]-[/dim]"

    # Created: created_by plus created_at, which is in MILLISECONDS.
    created_by = (spec.created_by if spec else None) or "-"
    created_cell = f"[dim]{created_by}[/dim]\n{format_timestamp_ms(meta.created_at)}"

    return (
        name_id,
        status_cell,
        nodes_cell,
        gpu_cell,
        users_cell,
        created_cell,
    )


@node.command(name="list-reservations")
@click.argument("name", type=str)
def list_reservations_command(name):
    """
    List node reservations under a node group.

    NAME is the node group name or ID (partial match supported, e.g. 'h100').
    For each reservation it shows the status, the desired/approved/reserved node
    counts (with the reserved node IDs), the GPU usage on the reserved nodes, the
    authorized users, and who created it and when.
    """
    node_groups = resolve_node_groups([name], is_exact_match=False)
    if not node_groups:
        return

    client = get_client()

    for node_group in node_groups:
        ng_name = node_group.metadata.name
        ng_id = node_group.metadata.id_

        try:
            reservations = client.nodegroup.list_reservations(node_group)
        except Exception as e:
            console.print(
                f"[red]Failed to fetch reservations for {ng_name} ({ng_id}):[/red] {e}"
            )
            continue

        if not reservations:
            console.print(
                f"[yellow]No reservations found in node group {ng_name}"
                f" ({ng_id}).[/yellow]"
            )
            continue

        # Reservations carry only node IDs; fetch the nodes once to resolve the
        # GPU usage of each reservation's reserved nodes.
        node_gpu_by_id = {}
        try:
            for node in client.nodegroup.list_nodes(node_group):
                resource = node.spec.resource if node.spec else None
                gpu = resource.gpu if resource else None
                if gpu is not None:
                    node_gpu_by_id[node.metadata.id_] = gpu
        except Exception as e:
            console.print(
                "[dim]Warning:[/dim] Failed to fetch nodes for GPU usage in"
                f" {ng_name} ({ng_id}): {e}"
            )

        table = Table(title=f"Reservations in {ng_name} ({ng_id})", show_lines=True)
        table.add_column("Reservation")
        table.add_column("Status")
        table.add_column("Nodes\n[dim](desired / approved / reserved)[/dim]")
        table.add_column("GPU Usage\n[dim](avail · used/total)[/dim]")
        table.add_column("Users")
        table.add_column("Created")

        for reservation in reservations:
            table.add_row(*_format_reservation_row(reservation, node_gpu_by_id))

        console.print(table)


@node.command(name="resource-shape")
@click.option(
    "--node-group",
    "-ng",
    help=(
        "Show resource shapes for specific node groups by their IDs or names. Can use"
        " partial name/ID (e.g., 'h100' will match any name/ID containing 'h100'). Can"
        " specify multiple values."
    ),
    type=str,
    required=False,
    multiple=True,
)
@click.option(
    "--purpose",
    help="Filter shapes by purpose (e.g. deployment|pod|job).",
    type=str,
    required=False,
)
def resource_shape_command(node_group=None, purpose=None):
    """
    List resource shapes per node group.

    Columns:
      - Node Group: name on first line, id on second line
      - Shapes: one shape per block, first line is name, second line shows colored availability for pod/endpoint/job
      - Detailed: description and colored resource details
    """
    client = APIClient()
    node_groups = client.nodegroup.list_all()

    if node_group:
        filters = node_group
        node_groups = [
            ng
            for ng in node_groups
            if any((f in ng.metadata.id_) or (f in ng.metadata.name) for f in filters)
        ]

    table = Table(title="Resource Shapes by Node Group", show_lines=True)
    table.add_column("Node Group")
    table.add_column("Shapes")
    table.add_column("Detailed")

    wanted = {str(purpose).lower()} if purpose else {"pod", "deployment", "job"}

    for ng in node_groups:
        ng_name = ng.metadata.name
        ng_id = ng.metadata.id_

        shapes = client.shapes.list_shapes(node_group=ng_id, purpose=purpose)
        # Fallback to name if ID returns nothing
        if not shapes:
            try:
                shapes = client.shapes.list_shapes(node_group=ng_name, purpose=purpose)
            except Exception:
                shapes = []

        # NodeGroup column: name on first line, id on second line (only show on the first row per group)
        filtered = []
        for sh in shapes:
            spec = getattr(sh, "spec", None)
            listable = set((getattr(spec, "listable_in", None) or []))
            listable_lower = {str(x).lower() for x in listable}
            if listable_lower & wanted:
                filtered.append(sh)

        if not filtered:
            nodegroup_text = f"{ng_name}\n[dim]{ng_id}[/dim]"
            table.add_row(nodegroup_text, "[yellow]- none[/yellow]", "")
            continue

        first = True
        for sh in filtered:
            shape_text, detail_text = _format_shape_entry(sh)
            nodegroup_text = f"{ng_name}\n[dim]{ng_id}[/dim]" if first else ""
            table.add_row(nodegroup_text, shape_text, detail_text)
            first = False

    console.print(table)


_NODE_STORAGE_NAME_PATTERN = re.compile(r"^[a-z]([-a-z0-9]*[a-z0-9])?$")
_OBJECT_STORAGE_NAME_PATTERN = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
_RESERVED_NODE_STORAGE_PATH = "/mnt/lepton-shared-fs"


def _node_storage_type(volume):
    from_source = getattr(volume, "from_", None)
    if from_source is None:
        return None

    source_str = str(
        from_source.value if hasattr(from_source, "value") else from_source
    ).lower()
    return f"node-{source_str}"


def _format_storage_type(volume):
    storage_type = _node_storage_type(volume)
    if storage_type is None:
        return "-"

    source_str = storage_type.removeprefix("node-")
    if source_str == "local":
        return f"[green]{storage_type}[/green]"
    if source_str == "nfs":
        return f"[cyan]{storage_type}[/cyan]"
    return storage_type


def _format_object_storage_path(data_source):
    object_storage = data_source.spec.object_
    bucket = object_storage.bucket
    provider_type = object_storage.provider.type_.lower()
    scheme = {
        "aws": "s3",
        "s3": "s3",
        "gcs": "gs",
    }.get(provider_type, provider_type)
    return f"{scheme}://{bucket}" if scheme and bucket else bucket or "-"


def _list_object_storage_data_sources(client, node_group):
    if not getattr(node_group.spec, "enable_object_storage", False):
        return []
    return client.nodegroup.list_storage_data_sources(node_group)


def _resolve_storage_node_group(client, node_group):
    node_groups = client.nodegroup.list_all()
    matches = [
        ng for ng in node_groups if node_group in (ng.metadata.id_, ng.metadata.name)
    ]

    if not matches:
        available = ", ".join(
            sorted(f"{ng.metadata.name} ({ng.metadata.id_})" for ng in node_groups)
        )
        message = f"Node group '{node_group}' was not found."
        if available:
            message += f" Available node groups: {available}."
        raise click.ClickException(message)
    if len(matches) > 1:
        matched = ", ".join(
            sorted(f"{ng.metadata.name} ({ng.metadata.id_})" for ng in matches)
        )
        raise click.ClickException(
            f"Node group '{node_group}' is ambiguous: {matched}. Use its ID."
        )
    return matches[0]


def _list_storage_volumes(node_group=None):
    client = APIClient()
    node_groups = client.nodegroup.list_all()

    if node_group:
        filters = node_group
        node_groups = [
            ng
            for ng in node_groups
            if any((f in ng.metadata.id_) or (f in ng.metadata.name) for f in filters)
        ]

    table = Table(title="Storage by Node Group", show_lines=True)
    table.add_column("Node Group")
    table.add_column("Type")
    table.add_column("Storage Name")
    table.add_column("Path")

    for ng in node_groups:
        ng_name = ng.metadata.name
        ng_id = ng.metadata.id_
        volumes = getattr(ng.spec, "volumes", None) or []
        data_sources = _list_object_storage_data_sources(client, ng)

        if not volumes and not data_sources:
            nodegroup_text = f"[bold]{ng_name}[/bold]\n[dim]{ng_id}[/dim]"
            table.add_row(nodegroup_text, "", "None", "")
            continue

        volume_name_lines = []
        volume_type_lines = []
        volume_path_lines = []
        for volume in volumes:
            volume_name_lines.append(getattr(volume, "name", None) or "-")
            volume_type_lines.append(_format_storage_type(volume))
            volume_path_lines.append(getattr(volume, "from_path", None) or "-")

        for data_source in data_sources:
            volume_name_lines.append(data_source.metadata.name or "-")
            volume_type_lines.append("[magenta]object-storage[/magenta]")
            volume_path_lines.append(_format_object_storage_path(data_source))

        nodegroup_text = f"[bold]{ng_name}[/bold]\n[dim]{ng_id}[/dim]"
        table.add_row(
            nodegroup_text,
            "\n".join(volume_type_lines),
            "\n".join(volume_name_lines),
            "\n".join(volume_path_lines),
        )

    console.print(table)

    console.print(
        "[dim]Note:[/dim] Node volume mount syntax: "
        "`--mount FROM_PATH:MOUNT_PATH:VOLUME` "
        "(split on the first two colons, so `VOLUME` may itself contain a "
        "colon).\n"
        "[dim]`VOLUME` is `node-local`, or `node-<type>:<storage_name>` for "
        "a named volume (e.g. `node-nfs:my-nfs`). Example: "
        "`/hf-cache:/root/.cache/huggingface:node-nfs:my-nfs`. Object Storage "
        "is a data source attachment and does not use this mount syntax.[/dim]"
    )


@node.group(name="storage", invoke_without_command=True)
@click.option(
    "--node-group",
    "-ng",
    help=(
        "Show storage for specific node groups by their IDs or names. Can use"
        " partial name/ID (e.g., 'h100' will match any name/ID containing 'h100'). Can"
        " specify multiple values."
    ),
    type=str,
    required=False,
    multiple=True,
)
@click.pass_context
def storage_group(ctx, node_group=None):
    """
    Manage storage configured for node groups.

    With no subcommand, lists each storage's name, type, and path.
    """
    if ctx.invoked_subcommand is None:
        _list_storage_volumes(node_group)


def _validate_node_storage_name(storage_name):
    if not _NODE_STORAGE_NAME_PATTERN.fullmatch(storage_name):
        raise click.BadParameter(
            "must start with a lowercase letter, contain only lowercase letters, "
            "numbers, and hyphens, and end with a letter or number.",
            param_hint="'--name' / '-n'",
        )


def _validate_object_storage_name(storage_name):
    if len(storage_name) > 63 or not _OBJECT_STORAGE_NAME_PATTERN.fullmatch(
        storage_name
    ):
        raise click.BadParameter(
            "must be no more than 63 characters, contain only lowercase letters, "
            "numbers, and hyphens, and start and end with a letter or number.",
            param_hint="'--name' / '-n'",
        )


def _required_object_storage_option(value, option, provider):
    if value is None or not value.strip():
        raise click.UsageError(
            f"Option '{option}' is required for {provider} Object Storage."
        )
    return value.strip()


def _build_object_storage_provider(
    provider,
    region,
    endpoint,
    project_id,
):
    provider = provider.lower()
    if provider in ("aws", "s3"):
        if project_id is not None:
            raise click.UsageError(
                "Option '--project-id' is only valid with provider 'gcs'."
            )
        region = _required_object_storage_option(
            region,
            "--region",
            provider,
        )
        if provider == "aws":
            config = {"region": region}
            if endpoint is not None:
                config["endpointUrl"] = endpoint.strip()
            return ObjectStorageProviderConfig(**{
                "type": provider,
                "aws": config,
            })

        endpoint = _required_object_storage_option(
            endpoint,
            "--endpoint",
            provider,
        )
        return ObjectStorageProviderConfig(**{
            "type": provider,
            "s3": {
                "region": region,
                "endpoint": endpoint,
            },
        })

    if region is not None or endpoint is not None:
        raise click.UsageError(
            "Options '--region' and '--endpoint' are only valid with providers "
            "'aws' and 's3'."
        )
    project_id = _required_object_storage_option(
        project_id,
        "--project-id",
        provider,
    )
    return ObjectStorageProviderConfig(**{
        "type": provider,
        "gcs": {"projectId": project_id},
    })


def _build_object_storage_credentials(
    provider,
    wif,
    access_key_secret_name,
    secret_key_secret_name,
):
    provider = provider.lower()
    has_access_key = access_key_secret_name is not None
    has_secret_key = secret_key_secret_name is not None

    if provider == "gcs":
        if has_access_key or has_secret_key:
            raise click.UsageError(
                "GCS requires WIF; do not provide secret credential options."
            )
        return {"type": "wif"}

    if wif and (has_access_key or has_secret_key):
        raise click.UsageError(
            "Use either '--wif' or both secret credential options, not both."
        )
    if wif:
        return {"type": "wif"}
    if has_access_key != has_secret_key:
        raise click.UsageError(
            "Options '--access-key-secret-name' and '--secret-key-secret-name' "
            "must be provided together."
        )
    if not has_access_key:
        raise click.UsageError(
            "Use '--wif' or provide both '--access-key-secret-name' and "
            "'--secret-key-secret-name'."
        )

    access_key_secret_name = access_key_secret_name.strip()
    secret_key_secret_name = secret_key_secret_name.strip()
    if not access_key_secret_name or not secret_key_secret_name:
        raise click.BadParameter(
            "must not be empty.",
            param_hint="'--access-key-secret-name' / '--secret-key-secret-name'",
        )
    return {
        "type": "leptonSecret",
        "leptonSecret": {
            "s3Credentials": {
                "accessKeySecretName": access_key_secret_name,
                "secretKeySecretName": secret_key_secret_name,
            },
        },
    }


@storage_group.command(name="add")
@click.option(
    "--node-group",
    "-ng",
    type=str,
    required=True,
    help="Exact node group name or ID.",
)
@click.option(
    "--type",
    "-t",
    "storage_type",
    type=click.Choice(
        ["node-local", "node-nfs", "object-storage"],
        case_sensitive=False,
    ),
    required=True,
    help="Storage type.",
)
@click.option(
    "--name",
    "-n",
    "storage_name",
    type=str,
    required=True,
    help="Storage name.",
)
@click.option(
    "--path",
    "--from-path",
    "-p",
    "from_path",
    type=str,
    required=False,
    help="Node Local path or the path where NFS is already mounted on each node.",
)
@click.option(
    "--provider",
    type=click.Choice(["aws", "s3", "gcs"], case_sensitive=False),
    required=False,
    help="Object Storage provider: AWS S3, S3 Compatible, or GCS.",
)
@click.option("--bucket", type=str, help="Object Storage bucket name.")
@click.option("--region", type=str, help="AWS or S3 Compatible region.")
@click.option(
    "--endpoint",
    type=str,
    help="Optional AWS endpoint or required S3 Compatible endpoint.",
)
@click.option("--project-id", type=str, help="GCP project ID for GCS.")
@click.option(
    "--wif",
    is_flag=True,
    help="Use Workload Identity Federation instead of secret credentials.",
)
@click.option(
    "--access-key-secret-name",
    "--access-key-secret",
    type=str,
    help="Workspace secret containing the access key ID.",
)
@click.option(
    "--secret-key-secret-name",
    "--secret-key-secret",
    type=str,
    help="Workspace secret containing the secret access key.",
)
@click.option(
    "--enable-aistore",
    is_flag=True,
    help="Enable AIStore fast caching. Always enabled for GCS.",
)
@click.option(
    "--user",
    "-u",
    "allowed_users",
    type=str,
    multiple=True,
    help=(
        "Restrict Object Storage to this workspace member. Can be repeated; "
        "omit for default workspace-wide access."
    ),
)
def add_storage_command(
    node_group,
    storage_type,
    storage_name,
    from_path,
    provider,
    bucket,
    region,
    endpoint,
    project_id,
    wif,
    access_key_secret_name,
    secret_key_secret_name,
    enable_aistore,
    allowed_users,
):
    """Add Node Local, NFS, or Object Storage to a node group."""
    storage_type = storage_type.lower()
    if storage_type in ("node-local", "node-nfs"):
        _validate_node_storage_name(storage_name)
        if any(
            value is not None
            for value in (
                provider,
                bucket,
                region,
                endpoint,
                project_id,
                access_key_secret_name,
                secret_key_secret_name,
            )
        ) or any((wif, enable_aistore, allowed_users)):
            raise click.UsageError(
                "Object Storage options can only be used with '--type object-storage'."
            )
        if from_path is None:
            raise click.UsageError(
                "Option '--path' / '--from-path' / '-p' is required for "
                "node-local and node-nfs storage."
            )
        from_path = from_path.strip()
        if not from_path.startswith("/"):
            raise click.BadParameter(
                "must be an absolute path starting with '/'.",
                param_hint="'--path' / '--from-path' / '-p'",
            )
        if from_path == _RESERVED_NODE_STORAGE_PATH:
            raise click.BadParameter(
                f"'{_RESERVED_NODE_STORAGE_PATH}' is reserved for "
                "Lepton-managed storage.",
                param_hint="'--path' / '--from-path' / '-p'",
            )

        client = APIClient()
        matched_node_group = _resolve_storage_node_group(client, node_group)
        existing_volumes = list(getattr(matched_node_group.spec, "volumes", None) or [])
        data_sources = _list_object_storage_data_sources(
            client,
            matched_node_group,
        )
        if any(volume.name == storage_name for volume in existing_volumes) or any(
            data_source.metadata.name == storage_name for data_source in data_sources
        ):
            raise click.ClickException(
                f"Storage '{storage_name}' already exists in node group "
                f"'{matched_node_group.metadata.name}'."
            )
        if any(
            (getattr(volume, "from_path", None) or "").strip() == from_path
            for volume in existing_volumes
        ):
            raise click.ClickException(
                f"Storage path '{from_path}' already exists in node group "
                f"'{matched_node_group.metadata.name}'."
            )

        from_source, creation_mode = {
            "node-local": (VolumeFrom.Local, VolumeCreationMode.Mkdir),
            "node-nfs": (VolumeFrom.NFS, VolumeCreationMode.NoneValue),
        }[storage_type]
        volume = Volume(**{
            "from": from_source,
            "name": storage_name,
            "size_in_gb": 0,
            "creation_mode": creation_mode,
            "from_path": from_path,
        })
        client.nodegroup.add_volume(matched_node_group, volume)
        console.print(
            f"Added [green]{storage_type}[/green] storage "
            f"[bold]{storage_name}[/bold] at [cyan]{from_path}[/cyan] to node group "
            f"[bold]{matched_node_group.metadata.name}[/bold]."
        )
        return

    _validate_object_storage_name(storage_name)
    if from_path is not None:
        raise click.UsageError(
            "Option '--path' is not used with '--type object-storage'."
        )
    if provider is None:
        raise click.UsageError("Option '--provider' is required for Object Storage.")
    bucket = _required_object_storage_option(
        bucket,
        "--bucket",
        provider.lower(),
    )
    provider_config = _build_object_storage_provider(
        provider,
        region,
        endpoint,
        project_id,
    )
    credentials = _build_object_storage_credentials(
        provider,
        wif,
        access_key_secret_name,
        secret_key_secret_name,
    )
    users = _permission_users(allowed_users)

    client = APIClient()
    matched_node_group = _resolve_storage_node_group(client, node_group)
    if not getattr(matched_node_group.spec, "enable_object_storage", False):
        raise click.ClickException(
            "Object Storage is not enabled for node group "
            f"'{matched_node_group.metadata.name}'."
        )
    existing_volumes = list(getattr(matched_node_group.spec, "volumes", None) or [])
    data_sources = _list_object_storage_data_sources(
        client,
        matched_node_group,
    )
    if any(volume.name == storage_name for volume in existing_volumes) or any(
        data_source.metadata.name == storage_name for data_source in data_sources
    ):
        raise click.ClickException(
            f"Storage '{storage_name}' already exists in node group "
            f"'{matched_node_group.metadata.name}'."
        )

    object_storage = ObjectStorageConfig(
        bucket=bucket,
        provider=provider_config,
        credentials=credentials,
        aistore=(
            {"enabled": True} if provider.lower() == "gcs" or enable_aistore else None
        ),
    )
    spec = StorageDataSourceSpec(**{
        "name": storage_name,
        "workspace": client.workspace_id,
        "description": "",
        "object": object_storage,
        "permissions": DataSourcePermissions(allowed_users=users) if users else None,
    })
    client.nodegroup.create_storage_data_source(
        matched_node_group,
        spec,
    )
    scheme = "gs" if provider.lower() == "gcs" else "s3"
    console.print(
        "Added [magenta]object-storage[/magenta] "
        f"[bold]{storage_name}[/bold] at [cyan]{scheme}://{bucket}[/cyan] "
        f"to node group [bold]{matched_node_group.metadata.name}[/bold]."
    )
    console.print(
        "[yellow]Note:[/yellow] Object Storage name, provider, bucket, "
        "region/endpoint/project ID, and AIStore setting are immutable after "
        "creation. To change them, delete and recreate the Object Storage."
    )


@storage_group.command(name="edit")
@click.option(
    "--node-group",
    "-ng",
    type=str,
    required=True,
    help="Exact node group name or ID.",
)
@click.option(
    "--name",
    "-n",
    "storage_name",
    type=str,
    required=True,
    help="Existing Object Storage name. Names cannot be changed.",
)
@click.option(
    "--provider",
    type=click.Choice(["aws", "s3", "gcs"], case_sensitive=False),
    help="Immutable after creation; delete and recreate to change.",
)
@click.option(
    "--bucket",
    type=str,
    help="Immutable after creation; delete and recreate to change.",
)
@click.option(
    "--region",
    type=str,
    help="Immutable after creation; delete and recreate to change.",
)
@click.option(
    "--endpoint",
    type=str,
    help="Immutable after creation; delete and recreate to change.",
)
@click.option(
    "--project-id",
    type=str,
    help="Immutable after creation; delete and recreate to change.",
)
@click.option(
    "--enable-aistore/--disable-aistore",
    "aistore_setting",
    default=None,
    help="Immutable after creation; delete and recreate to change.",
)
@click.option(
    "--wif",
    is_flag=True,
    help="Switch authentication to Workload Identity Federation.",
)
@click.option(
    "--access-key-secret-name",
    "--access-key-secret",
    type=str,
    help="Switch authentication using this access key ID secret.",
)
@click.option(
    "--secret-key-secret-name",
    "--secret-key-secret",
    type=str,
    help="Switch authentication using this secret access key secret.",
)
@click.option(
    "--user",
    "-u",
    "allowed_users",
    type=str,
    multiple=True,
    help="Replace the bucket allowlist with this member. Can be repeated.",
)
@click.option(
    "--all-members",
    is_flag=True,
    help="Clear the bucket allowlist and restore workspace-wide access.",
)
def edit_storage_command(
    node_group,
    storage_name,
    provider,
    bucket,
    region,
    endpoint,
    project_id,
    aistore_setting,
    wif,
    access_key_secret_name,
    secret_key_secret_name,
    allowed_users,
    all_members,
):
    """
    Edit Object Storage authentication or its bucket allowlist.

    Name, provider, bucket, region/endpoint/project ID, and AIStore settings
    are immutable after creation. To change them, delete and recreate the
    Object Storage.
    """
    immutable_options = [
        ("provider", provider is not None),
        ("bucket", bucket is not None),
        ("region", region is not None),
        ("endpoint", endpoint is not None),
        ("project ID", project_id is not None),
        ("AIStore setting", aistore_setting is not None),
    ]
    requested_immutable_fields = [
        name for name, requested in immutable_options if requested
    ]
    if requested_immutable_fields:
        raise click.UsageError(
            "Cannot change immutable Object Storage field(s): "
            f"{', '.join(requested_immutable_fields)}. No changes were made. "
            "Use `lep node storage delete` and `lep node storage add` to recreate "
            "the Object Storage."
        )

    users = _permission_users(allowed_users)
    if users and all_members:
        raise click.UsageError(
            "Use either '--user' / '-u' or '--all-members', not both."
        )
    credentials_requested = (
        wif or access_key_secret_name is not None or secret_key_secret_name is not None
    )
    permissions_requested = bool(users) or all_members
    if not credentials_requested and not permissions_requested:
        raise click.UsageError(
            "Specify authentication options, '--user' / '-u', or '--all-members'."
        )

    client = APIClient()
    matched_node_group = _resolve_storage_node_group(client, node_group)
    storage_kind, storage = _resolve_permission_storage(
        client,
        matched_node_group,
        storage_name,
    )
    if storage_kind != "object":
        raise click.ClickException(
            f"Storage '{storage_name}' is {_node_storage_type(storage)}; "
            "only Object Storage can be edited."
        )

    data_source = client.nodegroup.get_storage_data_source(
        matched_node_group,
        storage.metadata.name,
    )
    updated_spec = _copy_pydantic_model(data_source.spec)
    provider = updated_spec.object_.provider.type_.lower()
    if credentials_requested:
        updated_spec.object_.credentials = _build_object_storage_credentials(
            provider,
            wif,
            access_key_secret_name,
            secret_key_secret_name,
        )
    if permissions_requested:
        updated_spec.permissions = (
            None if all_members else DataSourcePermissions(allowed_users=users)
        )

    client.nodegroup.update_storage_data_source(
        matched_node_group,
        data_source.metadata.name,
        updated_spec,
    )
    changes = []
    if credentials_requested:
        changes.append("authentication")
    if permissions_requested:
        changes.append("bucket allowlist")
    console.print(
        f"Updated {' and '.join(changes)} for Object Storage "
        f"[bold]{storage_name}[/bold]."
    )


@storage_group.command(name="delete")
@click.option(
    "--node-group",
    "-ng",
    type=str,
    required=True,
    help="Exact node group name or ID.",
)
@click.option(
    "--name",
    "-n",
    "storage_name",
    type=str,
    required=True,
    help="Storage name.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Delete without asking for confirmation.",
)
def delete_storage_command(node_group, storage_name, yes):
    """Delete Node Local, NFS, or Object Storage from a node group."""
    client = APIClient()
    matched_node_group = _resolve_storage_node_group(client, node_group)
    storage_kind, storage = _resolve_permission_storage(
        client,
        matched_node_group,
        storage_name,
    )

    if storage_kind == "object":
        if not yes:
            confirmed = click.confirm(
                f"Delete Object Storage '{storage_name}' from node group "
                f"'{matched_node_group.metadata.name}'? This removes the data "
                "source configuration, not objects in the bucket, and will be "
                "rejected if a workload is using it.",
            )
            if not confirmed:
                console.print("Deletion cancelled.")
                return
        client.nodegroup.delete_storage_data_source(
            matched_node_group,
            storage.metadata.name,
        )
        console.print(
            "Deleted [magenta]object-storage[/magenta] "
            f"[bold]{storage_name}[/bold] from node group "
            f"[bold]{matched_node_group.metadata.name}[/bold]."
        )
        return

    storage_type = _node_storage_type(storage)
    if storage_type not in ("node-local", "node-nfs"):
        raise click.ClickException(
            f"Storage '{storage_name}' has unsupported type '{storage_type}'."
        )
    if getattr(storage, "managed_by_lepton", False):
        raise click.ClickException(
            f"Storage '{storage_name}' is managed by Lepton and cannot be deleted "
            "directly."
        )

    if not yes:
        confirmed = click.confirm(
            f"Delete {storage_type} storage '{storage_name}' from node group "
            f"'{matched_node_group.metadata.name}'? This detaches the volume but "
            "does not delete its data and may affect running workloads.",
        )
        if not confirmed:
            console.print("Deletion cancelled.")
            return

    client.nodegroup.delete_volume(matched_node_group, storage_name)
    console.print(
        f"Deleted [green]{storage_type}[/green] storage "
        f"[bold]{storage_name}[/bold] from node group "
        f"[bold]{matched_node_group.metadata.name}[/bold]."
    )


@storage_group.command(name="get")
@click.option(
    "--node-group",
    "-ng",
    type=str,
    required=True,
    help="Node group name or ID containing the storage.",
)
@click.option(
    "--name",
    "-n",
    "storage_name",
    type=str,
    required=True,
    help="Storage name.",
)
def get_storage_command(node_group, storage_name):
    """Get storage by node group and name."""
    client = APIClient()
    matched_node_group = _resolve_storage_node_group(client, node_group)
    volumes = getattr(matched_node_group.spec, "volumes", None) or []
    storage = next(
        (candidate for candidate in volumes if candidate.name == storage_name),
        None,
    )
    data_sources = _list_object_storage_data_sources(client, matched_node_group)
    if storage is None:
        storage = next(
            (
                candidate
                for candidate in data_sources
                if candidate.metadata.name == storage_name
            ),
            None,
        )
    if storage is None:
        available_names = [candidate.name for candidate in volumes]
        available_names.extend(
            candidate.metadata.name
            for candidate in data_sources
            if candidate.metadata.name
        )
        available = ", ".join(sorted(available_names))
        message = (
            f"Storage '{storage_name}' was not found in node group "
            f"'{matched_node_group.metadata.name}'."
        )
        if available:
            message += f" Available storage: {available}."
        raise click.ClickException(message)

    if hasattr(storage, "model_dump"):
        storage_data = storage.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
        )
    else:
        storage_data = storage.dict(by_alias=True, exclude_none=True)

    console.print_json(
        data={
            "node_group": {
                "id": matched_node_group.metadata.id_,
                "name": matched_node_group.metadata.name,
            },
            "storage": storage_data,
        }
    )


@storage_group.group(name="permission", invoke_without_command=True)
@click.option(
    "--node-group",
    "-ng",
    type=str,
    required=False,
    help="Exact node group name or ID containing the storage.",
)
@click.option(
    "--name",
    "-n",
    "storage_name",
    type=str,
    required=False,
    help="Storage name. Omit to list permissions for all storage in the node group.",
)
@click.pass_context
def storage_permission_group(ctx, node_group, storage_name):
    """
    Manage storage permissions.

    With no subcommand, lists permissions. Node Local and NFS volumes use
    path-scoped rules; Object Storage uses a bucket-wide member allowlist.
    """
    if ctx.invoked_subcommand is not None:
        return
    if not node_group:
        raise click.UsageError(
            "Option '--node-group' / '-ng' is required when listing permissions."
        )
    _list_storage_permissions(node_group, storage_name)


def _list_storage_permissions(node_group, storage_name):
    """
    List storage permissions.

    Node Local and NFS volumes use path-scoped rules. Object Storage uses a
    bucket-wide member allowlist.
    """
    client = APIClient()
    matched_node_group = _resolve_storage_node_group(client, node_group)
    all_volumes = list(getattr(matched_node_group.spec, "volumes", None) or [])
    all_data_sources = _list_object_storage_data_sources(
        client,
        matched_node_group,
    )
    volumes = all_volumes
    data_sources = all_data_sources

    if storage_name:
        volumes = [volume for volume in volumes if volume.name == storage_name]
        data_sources = [
            data_source
            for data_source in data_sources
            if data_source.metadata.name == storage_name
        ]

    matching_storage_count = len(volumes) + len(data_sources)
    if matching_storage_count == 0:
        available_names = [volume.name for volume in all_volumes]
        available_names.extend(
            data_source.metadata.name
            for data_source in all_data_sources
            if data_source.metadata.name
        )
        if storage_name:
            message = (
                f"Storage '{storage_name}' was not found in node group "
                f"'{matched_node_group.metadata.name}'."
            )
            if available_names:
                message += f" Available storage: {', '.join(sorted(available_names))}."
            raise click.ClickException(message)
        raise click.ClickException(
            f"No storage was found in node group '{matched_node_group.metadata.name}'."
        )
    if storage_name and matching_storage_count > 1:
        raise click.ClickException(
            f"Storage name '{storage_name}' is used by more than one storage type in "
            f"node group '{matched_node_group.metadata.name}'."
        )

    table = Table(
        title=(
            f"Storage Permissions for {matched_node_group.metadata.name} "
            f"({matched_node_group.metadata.id_})"
        ),
        show_lines=True,
    )
    table.add_column("Storage", overflow="fold")
    table.add_column("Type", overflow="fold")
    table.add_column("Permission", overflow="fold")

    for volume in volumes:
        permissions = client.nodegroup.list_storage_permissions(
            matched_node_group,
            volume.name,
        )
        if not permissions:
            table.add_row(
                volume.name,
                _format_storage_type(volume),
                "[dim]Scope:[/dim] All paths\n"
                "[dim]Model:[/dim] [green]Default access[/green]\n"
                "[dim]Members:[/dim] All workspace members",
            )
            continue

        for permission in permissions:
            if permission.subfolder_policy == "by_user":
                scope = f"{permission.path_prefix.rstrip('/')}/<email_username>"
                permission_model = "Username subfolder rule"
                members = "Matching workspace member"
            else:
                scope = permission.path_prefix
                permission_model = "Path allow rule"
                members = (
                    "All workspace members"
                    if "*" in permission.allowed_users
                    else "\n".join(permission.allowed_users) or "-"
                )
            table.add_row(
                volume.name,
                _format_storage_type(volume),
                f"[dim]Scope:[/dim] {scope}\n"
                f"[dim]Model:[/dim] {permission_model}\n"
                f"[dim]Members:[/dim] {members}",
            )

    for data_source in data_sources:
        permissions = data_source.spec.permissions
        allowed_users = permissions.allowed_users if permissions else None
        table.add_row(
            data_source.metadata.name or "-",
            "[magenta]object-storage[/magenta]",
            f"[dim]Bucket:[/dim] {_format_object_storage_path(data_source)}\n"
            "[dim]Model:[/dim] "
            + (
                "Bucket allowlist\n"
                if allowed_users
                else "[green]Default access[/green]\n"
            )
            + "[dim]Members:[/dim] "
            + (
                "All workspace members"
                if not allowed_users or "*" in allowed_users
                else "\n".join(allowed_users)
            ),
        )

    console.print(table)
    console.print(
        "[dim]Note:[/dim] Node Local/NFS rules apply to paths within a volume. "
        "Object Storage permissions apply to the whole bucket. With no rules or "
        "allowlist, all workspace members have access."
    )


def _resolve_permission_storage(client, node_group, storage_name):
    volumes = list(getattr(node_group.spec, "volumes", None) or [])
    data_sources = _list_object_storage_data_sources(client, node_group)
    matches = [("volume", volume) for volume in volumes if volume.name == storage_name]
    matches.extend(
        ("object", data_source)
        for data_source in data_sources
        if data_source.metadata.name == storage_name
    )

    if not matches:
        available_names = [volume.name for volume in volumes]
        available_names.extend(
            data_source.metadata.name
            for data_source in data_sources
            if data_source.metadata.name
        )
        message = (
            f"Storage '{storage_name}' was not found in node group "
            f"'{node_group.metadata.name}'."
        )
        if available_names:
            message += f" Available storage: {', '.join(sorted(available_names))}."
        raise click.ClickException(message)
    if len(matches) > 1:
        raise click.ClickException(
            f"Storage name '{storage_name}' is used by more than one storage type in "
            f"node group '{node_group.metadata.name}'."
        )
    return matches[0]


def _permission_users(allowed_users, all_members=False):
    users = []
    for user in allowed_users:
        user = user.strip()
        if not user:
            raise click.BadParameter(
                "must not be empty.",
                param_hint="'--user' / '-u'",
            )
        if user not in users:
            users.append(user)

    if all_members and users:
        raise click.UsageError(
            "Use either '--user' / '-u' or '--all-members', not both."
        )
    return ["*"] if all_members else users


def _permission_path(path_prefix):
    if path_prefix is None:
        return None
    path_prefix = path_prefix.strip()
    if not path_prefix.startswith("/"):
        raise click.BadParameter(
            "must be an absolute path starting with '/'.",
            param_hint="'--path' / '-p'",
        )
    return path_prefix


def _copy_pydantic_model(model):
    if hasattr(model, "model_copy"):
        return model.model_copy(deep=True)
    return model.copy(deep=True)


@storage_permission_group.command(name="add")
@click.option(
    "--node-group",
    "-ng",
    type=str,
    required=True,
    help="Exact node group name or ID containing the storage.",
)
@click.option(
    "--name",
    "-n",
    "storage_name",
    type=str,
    required=True,
    help="Storage name.",
)
@click.option(
    "--path",
    "-p",
    "path_prefix",
    type=str,
    required=False,
    help="Path prefix for Node Local/NFS. Not used by Object Storage.",
)
@click.option(
    "--user",
    "-u",
    "allowed_users",
    type=str,
    multiple=True,
    help="Allowed workspace member. Can be repeated.",
)
@click.option(
    "--all-members",
    is_flag=True,
    help="Allow every workspace member.",
)
@click.option(
    "--by-user",
    is_flag=True,
    help="Allow each member only under a matching <email_username> subfolder.",
)
def add_storage_permission_command(
    node_group,
    storage_name,
    path_prefix,
    allowed_users,
    all_members,
    by_user,
):
    """Add a path rule or members to an Object Storage allowlist."""
    client = APIClient()
    matched_node_group = _resolve_storage_node_group(client, node_group)
    storage_kind, storage = _resolve_permission_storage(
        client,
        matched_node_group,
        storage_name,
    )
    users = _permission_users(allowed_users, all_members)
    path_prefix = _permission_path(path_prefix)

    if storage_kind == "volume":
        if path_prefix is None:
            raise click.UsageError(
                "Option '--path' / '-p' is required for node-local and node-nfs "
                "permissions."
            )
        if by_user and users:
            raise click.UsageError(
                "Use either '--by-user' or member options, not both."
            )
        if not by_user and not users:
            raise click.UsageError(
                "Use '--user' / '-u', '--all-members', or '--by-user'."
            )

        permissions = client.nodegroup.list_storage_permissions(
            matched_node_group,
            storage.name,
        )
        if any(permission.path_prefix == path_prefix for permission in permissions):
            raise click.ClickException(
                f"Permission for path '{path_prefix}' already exists on storage "
                f"'{storage_name}'."
            )

        permission = StoragePermission(
            path_prefix=path_prefix,
            allowed_users=[] if by_user else users,
            subfolder_policy="by_user" if by_user else "",
            nodegroup_id=matched_node_group.metadata.id_,
        )
        client.nodegroup.set_storage_permission(
            matched_node_group,
            storage.name,
            permission,
        )
        console.print(
            f"Added permission for [cyan]{path_prefix}[/cyan] on "
            f"[bold]{_node_storage_type(storage)}:{storage_name}[/bold]."
        )
        if not permissions:
            console.print(
                "[yellow]Note:[/yellow] This is the first path rule, so storage "
                "access is now restricted to explicitly permitted paths."
            )
        return

    if path_prefix is not None or by_user:
        raise click.UsageError(
            "Object Storage permissions are bucket-wide; do not use '--path' or "
            "'--by-user'."
        )
    if not users:
        raise click.UsageError(
            "Use '--user' / '-u' or '--all-members' for Object Storage."
        )

    data_source = client.nodegroup.get_storage_data_source(
        matched_node_group,
        storage.metadata.name,
    )
    current_permissions = data_source.spec.permissions
    current_users = (
        list(current_permissions.allowed_users or []) if current_permissions else []
    )
    if "*" in users:
        updated_users = ["*"]
    elif "*" in current_users:
        raise click.ClickException(
            f"Object Storage '{storage_name}' already allows all workspace members."
        )
    else:
        updated_users = current_users + [
            user for user in users if user not in current_users
        ]
    if updated_users == current_users:
        raise click.ClickException(
            "Every specified member is already in the bucket allowlist."
        )

    updated_spec = _copy_pydantic_model(data_source.spec)
    updated_spec.permissions = DataSourcePermissions(
        allowed_users=updated_users,
    )
    client.nodegroup.update_storage_data_source(
        matched_node_group,
        data_source.metadata.name,
        updated_spec,
    )
    console.print(
        "Updated bucket allowlist for Object Storage "
        f"[bold]{storage_name}[/bold]: {', '.join(updated_users)}."
    )
    if not current_users and "*" not in updated_users:
        console.print(
            "[yellow]Note:[/yellow] The bucket previously had default workspace-wide "
            "access and is now restricted to the listed members."
        )


@storage_permission_group.command(name="delete")
@click.option(
    "--node-group",
    "-ng",
    type=str,
    required=True,
    help="Exact node group name or ID containing the storage.",
)
@click.option(
    "--name",
    "-n",
    "storage_name",
    type=str,
    required=True,
    help="Storage name.",
)
@click.option(
    "--path",
    "-p",
    "path_prefix",
    type=str,
    required=False,
    help="Path rule to delete from Node Local/NFS.",
)
@click.option(
    "--user",
    "-u",
    "allowed_users",
    type=str,
    multiple=True,
    help="Member to remove from an Object Storage allowlist. Can be repeated.",
)
@click.option(
    "--clear",
    is_flag=True,
    help="Clear the entire Object Storage allowlist.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Delete without asking for confirmation.",
)
def delete_storage_permission_command(
    node_group,
    storage_name,
    path_prefix,
    allowed_users,
    clear,
    yes,
):
    """Delete a path rule or members from an Object Storage allowlist."""
    client = APIClient()
    matched_node_group = _resolve_storage_node_group(client, node_group)
    storage_kind, storage = _resolve_permission_storage(
        client,
        matched_node_group,
        storage_name,
    )
    users = _permission_users(allowed_users)
    path_prefix = _permission_path(path_prefix)

    if storage_kind == "volume":
        if path_prefix is None:
            raise click.UsageError(
                "Option '--path' / '-p' is required for node-local and node-nfs "
                "permissions."
            )
        if users or clear:
            raise click.UsageError(
                "Node Local/NFS deletion removes an entire path rule; do not use "
                "'--user' or '--clear'."
            )

        permissions = client.nodegroup.list_storage_permissions(
            matched_node_group,
            storage.name,
        )
        if not any(permission.path_prefix == path_prefix for permission in permissions):
            raise click.ClickException(
                f"Permission for path '{path_prefix}' was not found on storage "
                f"'{storage_name}'."
            )
        restores_default_access = len(permissions) == 1
        if not yes:
            prompt = (
                f"Delete permission for path '{path_prefix}' from '{storage_name}'?"
            )
            if restores_default_access:
                prompt += (
                    " This is the final rule, so all workspace members will regain "
                    "default access to all paths."
                )
            if not click.confirm(prompt):
                console.print("Permission deletion cancelled.")
                return

        client.nodegroup.delete_storage_permission(
            matched_node_group,
            storage.name,
            path_prefix,
        )
        console.print(
            f"Deleted permission for [cyan]{path_prefix}[/cyan] from "
            f"[bold]{_node_storage_type(storage)}:{storage_name}[/bold]."
        )
        if restores_default_access:
            console.print(
                "[yellow]Note:[/yellow] No path rules remain; all workspace members "
                "now have default access."
            )
        return

    if path_prefix is not None:
        raise click.UsageError(
            "Object Storage permissions are bucket-wide; do not use '--path'."
        )
    if clear and users:
        raise click.UsageError("Use either '--user' / '-u' or '--clear', not both.")
    if not clear and not users:
        raise click.UsageError(
            "Use '--user' / '-u' to remove members or '--clear' to clear the "
            "Object Storage allowlist."
        )

    data_source = client.nodegroup.get_storage_data_source(
        matched_node_group,
        storage.metadata.name,
    )
    current_permissions = data_source.spec.permissions
    current_users = (
        list(current_permissions.allowed_users or []) if current_permissions else []
    )
    if not current_users:
        raise click.ClickException(
            f"Object Storage '{storage_name}' has no bucket allowlist and already "
            "uses default workspace-wide access."
        )

    if clear:
        updated_users = []
    else:
        missing_users = [user for user in users if user not in current_users]
        if missing_users:
            raise click.ClickException(
                "Member(s) not found in the bucket allowlist: "
                f"{', '.join(missing_users)}."
            )
        users_to_remove = set(users)
        updated_users = [user for user in current_users if user not in users_to_remove]
    restores_default_access = not updated_users

    if not yes:
        if clear:
            prompt = f"Clear the bucket allowlist for '{storage_name}'?"
        else:
            prompt = (
                f"Remove {', '.join(users)} from the bucket allowlist for "
                f"'{storage_name}'?"
            )
        if restores_default_access:
            prompt += (
                " No allowlist will remain, so all workspace members will regain "
                "default access."
            )
        if not click.confirm(prompt):
            console.print("Permission deletion cancelled.")
            return

    updated_spec = _copy_pydantic_model(data_source.spec)
    updated_spec.permissions = (
        DataSourcePermissions(allowed_users=updated_users) if updated_users else None
    )
    client.nodegroup.update_storage_data_source(
        matched_node_group,
        data_source.metadata.name,
        updated_spec,
    )
    if updated_users:
        console.print(
            "Updated bucket allowlist for Object Storage "
            f"[bold]{storage_name}[/bold]: {', '.join(updated_users)}."
        )
    else:
        console.print(
            "Cleared the bucket allowlist for Object Storage "
            f"[bold]{storage_name}[/bold]."
        )
        console.print(
            "[yellow]Note:[/yellow] All workspace members now have default access."
        )


def add_command(cli_group):
    cli_group.add_command(node)
