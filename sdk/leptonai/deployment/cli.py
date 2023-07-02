from datetime import datetime
import sys

import click
from rich.console import Console
from rich.table import Table

import leptonai.workspace as workspace
from leptonai.util import click_group
from . import api


console = Console(highlight=False)


@click_group()
def deployment():
    pass


@deployment.command()
def create():
    console.print("Please use `lep photon run` instead.")
    sys.exit(1)


@deployment.command()
def list():
    workspace_url = workspace.get_workspace_url()
    if workspace_url is None:
        console.print("No workspace found. Please run `lep workspace login` first.")
        sys.exit(1)
    auth_token = workspace.cli.get_auth_token(workspace_url)
    deployments = api.list_remote(workspace_url, auth_token)
    records = [
        (d["name"], d["photon_id"], d["created_at"] / 1000, d["status"])
        for d in deployments
    ]
    if len(records) == 0:
        console.print(
            "No deployments found. Use `lep photon run` to create deployments."
        )
        return 0

    table = Table(title="deployments", show_lines=True)
    table.add_column("name")
    table.add_column("photon id")
    table.add_column("created at")
    table.add_column("status")
    table.add_column("endpoint", overflow="fold")
    for name, photon_id, created_at, status in records:
        table.add_row(
            name,
            photon_id,
            datetime.fromtimestamp(created_at).strftime("%Y-%m-%d\n%H:%M:%S"),
            status["state"],
            "\n".join(
                [
                    status["endpoint"]["internal_endpoint"],
                    status["endpoint"]["external_endpoint"],
                ]
            ),
        )
    console.print(table)


@deployment.command()
@click.option("--name", "-n", help="deployment name")
def remove(name):
    workspace_url = workspace.get_workspace_url()
    if workspace_url is None:
        console.print("No workspace found. Please run `lep workspace login` first.")
        sys.exit(1)
    auth_token = workspace.cli.get_auth_token(workspace_url)
    api.remove_remote(workspace_url, auth_token, name)
    console.print(f"deployment deleted successfully: {name}.")


def add_command(cli_group):
    cli_group.add_command(deployment)
