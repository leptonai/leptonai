import click

from rich.table import Table

from .util import (
    console,
    click_group,
)
from ..api.v2.client import APIClient


@click_group()
def node():
    """
    Manage nodes on the Lepton AI cloud.
    """
    pass


def _is_node_used(node):
    """Check if a node is in use"""
    return node.status.workloads and len(node.status.workloads) > 0


def _is_node_unhealthy(node):
    """Check if a node is unhealthy"""
    return "Unhealthy" in node.status.status


def _is_node_available(node):
    """
    Check if a node is available for use.

    A node is considered available when it meets ALL of the following conditions:
    1. Has no workloads on GPU(No workload used gpu)
    2. Is in Ready state (has 'Ready' in node.status.status)
    3. Is not marked as unschedulable (node.spec.unschedulable is False)
    4. Is not unhealthy (does not have 'Unhealthy' in node.status.status)
    """
    gpu_used = False
    if node.status.workloads:
        for workload in node.status.workloads:
            if workload.gpu_count and workload.gpu_count > 0:
                gpu_used = True
    return (
        not node.spec.unschedulable
        and "Ready" in node.status.status
        and "Unhealthy" not in node.status.status
        and not gpu_used
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
    client = APIClient()
    node_groups = client.nodegroup.list_all()

    if node_group:
        filtered_groups = []
        for ng_id_or_name_partial in node_group:
            filtered_groups.extend([
                ng
                for ng in node_groups
                if ng_id_or_name_partial in ng.metadata.id_
                or ng_id_or_name_partial in ng.metadata.name
            ])
        node_groups = filtered_groups

    console.print(
        "\n If a node appears available but is actually in use, it is currently"
        " handling only CPU workloads, with all GPUs remaining idle."
    )

    # Create base table
    table = Table(title="Node Groups", show_lines=True)
    table.add_column("Name")
    table.add_column("ID")
    table.add_column("Available Nodes (All GPU available)")
    table.add_column("Unhealthy Nodes")
    table.add_column("Used Nodes")
    table.add_column("Ready Nodes")

    # Add extra column for detailed view
    for node_group in node_groups:
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


def add_command(cli_group):
    cli_group.add_command(node)
