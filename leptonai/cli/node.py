import click

from rich.table import Table

from .util import (
    console,
    click_group,
)
from ..api.v1.client import APIClient


@click_group()
def node():
    """
    Manage nodes on the Lepton AI cloud.
    """
    pass


@node.command(name="list")
@click.option("--detail", "-d", help="Show all the nodes", is_flag=True)
def list_command(detail=False):
    """
    Lists all node groups in the current workspace.

    If the --detail or -d option is provided, additional information about each node will be displayed.
    """
    client = APIClient()
    node_groups = client.nodegroup.list_all()
    table = Table(title="Node Groups", show_lines=True)
    table.add_column("Name")
    table.add_column("ID")
    table.add_column("Ready Nodes")
    if detail:
        table.add_column("Nodes")
    for node_group in node_groups:
        node_group_name = node_group.metadata.name
        node_group_id = node_group.metadata.id_
        ready_nodes = str(node_group.status.ready_nodes)
        if detail:
            nodes = client.nodegroup.list_nodes(node_group)
            nodes_name = ""
            for node in nodes:
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
                nodes_name += f"{node_id}, ({node_cpu}, {node_gpu}),\n"
            table.add_row(node_group_name, node_group_id, ready_nodes, nodes_name)
        else:
            table.add_row(node_group_name, node_group_id, ready_nodes)
    console.print(table)


def add_command(cli_group):
    cli_group.add_command(node)
