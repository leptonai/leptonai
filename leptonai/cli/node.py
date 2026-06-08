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


@click_group()
def node():
    """
    Manage nodes on the DGX Cloud Lepton.
    """
    pass


def _is_node_usable(node):
    """A node is usable when it is ready, healthy, and schedulable."""
    status = (node.status.status if node.status else None) or []
    return (
        not node.spec.unschedulable and "Ready" in status and "Unhealthy" not in status
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
                stats["gpu_avail"] += total - used
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
    avail = (gpu.total - allocated) if usable else 0
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
                f"[dim]Warning:[/dim] Failed to fetch nodes for GPU usage in"
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


@node.command(name="storage")
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
def storage_command(node_group=None):
    """
    List storage volumes configured for node groups.

    Shows the volumes attached to each node group including their size,
    source, mount path, and creation mode.
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

    table = Table(title="Storage Volumes by Node Group", show_lines=True)
    table.add_column("Node Group")
    table.add_column("Storage Name")
    table.add_column("Type")

    for ng in node_groups:
        ng_name = ng.metadata.name
        ng_id = ng.metadata.id_
        volumes = getattr(ng.spec, "volumes", None) or []

        if not volumes:
            nodegroup_text = f"[bold]{ng_name}[/bold]\n[dim]{ng_id}[/dim]"
            table.add_row(nodegroup_text, "None", "")
            continue

        volume_name_lines = []
        volume_type_lines = []
        for vol in volumes:
            volume_name = getattr(vol, "name", "-")
            from_source = getattr(vol, "from_", None)

            if from_source is not None and from_source != "-":
                source_str = str(
                    from_source.value if hasattr(from_source, "value") else from_source
                ).lower()
                if source_str == "local":
                    type_text = f"[green]node-{source_str}[/green]"
                elif source_str == "nfs":
                    type_text = f"[cyan]node-{source_str}[/cyan]"
                else:
                    type_text = f"node-{source_str}"
            else:
                type_text = "-"

            volume_name_lines.append(volume_name)
            volume_type_lines.append(type_text)

        nodegroup_text = f"[bold]{ng_name}[/bold]\n[dim]{ng_id}[/dim]"
        table.add_row(
            nodegroup_text,
            "\n".join(volume_name_lines),
            "\n".join(volume_type_lines),
        )

    console.print(table)

    console.print(
        "[dim]Note:[/dim] Mount syntax: "
        "`--mount FROM_PATH:MOUNT_PATH:VOLUME` "
        "(split on the first two colons, so `VOLUME` may itself contain a "
        "colon).\n"
        "[dim]`VOLUME` is `node-local`, or `node-<type>:<storage_name>` for "
        "a named volume (e.g. `node-nfs:my-nfs`). Example: "
        "`/hf-cache:/root/.cache/huggingface:node-nfs:my-nfs`.[/dim]"
    )


def add_command(cli_group):
    cli_group.add_command(node)
