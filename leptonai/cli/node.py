import click

from rich.table import Table

from .util import (
    console,
    click_group,
    get_client,
    resolve_node_groups,
)
from ..api.v2.client import APIClient


@click_group()
def node():
    """
    Manage nodes on the DGX Cloud Lepton.
    """
    pass


def _is_node_used(node):
    """Check if a node is in use"""
    return node.status.workloads and len(node.status.workloads) > 0


def _is_node_unhealthy(node):
    """Check if a node is unhealthy"""
    return "Unhealthy" in node.status.status


def _is_node_available(node, skip_gpu_check=True):
    """
    Check if a node is available for use.

    A node is considered available when it meets ALL of the following conditions:
    1. Has no workloads on GPU(No workload used gpu)
    2. Is in Ready state (has 'Ready' in node.status.status)
    3. Is not marked as unschedulable (node.spec.unschedulable is False)
    4. Is not unhealthy (does not have 'Unhealthy' in node.status.status)
    """
    resource_used = False
    if not skip_gpu_check:

        if node.status.workloads:
            for workload in node.status.workloads:
                if workload.gpu_count and workload.gpu_count > 0:
                    resource_used = True
    else:
        if node.status.workloads and len(node.status.workloads) > 0:
            resource_used = True

    return (
        not node.spec.unschedulable
        and "Ready" in node.status.status
        and "Unhealthy" not in node.status.status
        and not resource_used
    )


def _get_node_stats(nodes):
    """Calculate node statistics"""
    used_nodes = 0
    unhealthy_nodes = 0
    available_nodes = 0
    unhealthy_node_details = []
    used_node_details = []
    available_node_details = []
    ready_node_details = []
    for node in nodes:
        node_details = _format_node_details(node)

        ready_node_details.append(node_details)

        if _is_node_used(node):
            used_nodes += 1
            used_node_details.append(node_details)

        if _is_node_unhealthy(node):
            unhealthy_nodes += 1
            unhealthy_node_details.append(node_details)

        if _is_node_available(node):
            available_nodes += 1
            available_node_details.append(node_details)

    return {
        "used": used_nodes,
        "unhealthy": unhealthy_nodes,
        "available": available_nodes,
        "unhealthy_nodes_details": unhealthy_node_details,
        "used_nodes_details": used_node_details,
        "available_nodes_details": available_node_details,
        "ready_nodes_details": ready_node_details,
    }


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


def _format_node_details(node):
    """Format detailed information for a single node"""
    node_id = node.metadata.id_
    node_cpu = (
        node.spec.resource.cpu.type_
        if (node.spec and node.spec.resource and node.spec.resource.cpu)
        else None
    )
    node_gpu = (
        node.spec.resource.gpu.product
        if (node.spec and node.spec.resource and node.spec.resource.gpu)
        else None
    )
    colored_statuses = [f"{_colorize_status(status)}" for status in node.status.status]
    return (
        f"[bold]{node_id}[/bold], ({node_cpu}, {node_gpu},"
        f" {', '.join(colored_statuses)},"
        f" {'[green]Idle[/green]' if node.status.workloads is None or len(node.status.workloads) == 0 else '[blue]Used[/blue]'})"
    )


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
@click.option("--detail", "-d", help="Show all the nodes", is_flag=True)
@click.option(
    "--node-group",
    "-ng",
    help=(
        "Show all the nodes in specific node groups by their IDs or names. Can use"
        " partial name/ID (e.g., 'h100' will match any name/ID containing 'h100'). Can"
        " specify multiple values."
    ),
    type=str,
    required=False,
    multiple=True,
)
def list_command(detail=False, node_group=None):
    """
    Lists all node groups in the current workspace.

    If the --detail or -d option is provided, additional information about each node will be displayed.
    """
    client = get_client()

    if node_group:
        filtered_node_groups = resolve_node_groups(node_group, is_exact_match=False)
    else:
        filtered_node_groups = client.nodegroup.list_all()

    # Create base table
    table = Table(title="Node Groups", show_lines=True)
    table.add_column("Name")
    table.add_column("ID")
    table.add_column("Fully Available Nodes")
    table.add_column("Unhealthy Nodes")
    table.add_column("Used Nodes")
    table.add_column("Ready Nodes")

    # Add extra column for detailed view
    for node_group in filtered_node_groups:
        node_group_name = node_group.metadata.name
        node_group_id = node_group.metadata.id_
        ready_nodes = str(node_group.status.ready_nodes or 0)

        # Get node list and calculate statistics
        nodes = client.nodegroup.list_nodes(node_group)
        stats = _get_node_stats(nodes)

        if detail:
            # Format node details by category
            used_details = "\n".join(stats["used_nodes_details"])
            unhealthy_details = "\n".join(stats["unhealthy_nodes_details"])
            available_details = "\n".join(stats["available_nodes_details"])
            ready_nodes_details = "\n".join(stats["ready_nodes_details"])

            table.add_row(
                node_group_name,
                node_group_id,
                f"[green]{stats['available']}[/green]/{ready_nodes}\n{available_details}",
                f"[red]{stats['unhealthy']}[/red]/{ready_nodes}\n{unhealthy_details}",
                f"[blue]{stats['used']}[/blue]/{ready_nodes}\n{used_details}",
                f"{ready_nodes}\n{ready_nodes_details}",
            )
        else:
            table.add_row(
                node_group_name,
                node_group_id,
                f"[green]{stats['available']}[/green]/{ready_nodes}",
                f"[red]{stats['unhealthy']}[/red]/{ready_nodes}",
                f"[blue]{stats['used']}[/blue]/{ready_nodes}",
                ready_nodes,
            )

    console.print(table)
    console.print(
        "\n[dim]Note:[/dim] 'Fully available' means the node has no workloads (CPU or"
        " GPU) and is Ready. Nodes with CPU-only workloads or partially used GPUs are"
        " not counted here, but may still accept small/fractional jobs depending on"
        " scheduler policies."
    )


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
def resource_shape_command(node_group=None):
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

    wanted = {"pod", "deployment", "job"}

    for ng in node_groups:
        ng_name = ng.metadata.name
        ng_id = ng.metadata.id_

        shapes = client.shapes.list_shapes(node_group=ng_id)
        # Fallback to name if ID returns nothing
        if not shapes:
            try:
                shapes = client.shapes.list_shapes(node_group=ng_name)
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


def add_command(cli_group):
    cli_group.add_command(node)
