import json

import click
from datetime import datetime
from rich.table import Table
from .util import console, click_group
from leptonai.api.v1.client import APIClient


@click_group()
def ingress():
    pass


@ingress.command(name="list")
def list_all():
    """
    List all ingress
    """
    client = APIClient()
    ingress_list = client.ingress.list_all()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name")
    table.add_column("Created At")
    table.add_column("Domain Name")
    table.add_column("Status")
    for ingress in ingress_list:
        created_time = datetime.fromtimestamp(
            ingress.metadata.created_at / 1000
        ).strftime("%Y-%m-%d\n%H:%M:%S")

        table.add_row(
            ingress.metadata.name,
            created_time,
            ingress.spec.domain_name,
            ingress.status.message,
        )
    table.title = "Ingress"
    console.print(table)


@ingress.command()
@click.option("--name", "-n", help="name of the ingress", type=str, required=True)
def get(name):
    """
    Get a ingress by name and print it in json
    """
    client = APIClient()
    ingress = client.ingress.get(name)
    console.print(f"Ingress details for [green]{name}[/]:")
    console.print(json.dumps(client.ingress.safe_json(ingress), indent=2))


@ingress.command()
@click.option("--name", "-n", help="name of the ingress", type=str, required=True)
def delete(name):
    """
    Delete a ingress by name
    """
    client = APIClient()
    client.ingress.delete(name)
    console.print(f"Ingress [green]{name}[/] deleted successfully.")


def add_command(cli_group):
    cli_group.add_command(ingress)
