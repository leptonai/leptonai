from datetime import datetime
import sys

import click
from rich.console import Console
from rich.table import Table

import leptonai.remote as remote
from . import api


console = Console(highlight=False)


@click.group()
def deployment():
    pass


@deployment.command()
def create():
    console.print("Please use `lep photon run` instead.")
    sys.exit(1)


@deployment.command()
def list():
    remote_url = remote.get_remote_url()
    if remote_url is None:
        console.print("No remote URL found. Please run `lep remote login` first.")
        sys.exit(1)
    auth_token = remote.cli.get_auth_token(remote_url)
    deployments = api.list_remote(remote_url, auth_token)
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
    remote_url = remote.get_remote_url()
    if remote_url is None:
        console.print("No remote URL found. Please run `lep remote login` first.")
        sys.exit(1)
    auth_token = remote.cli.get_auth_token(remote_url)
    api.remove_remote(remote_url, auth_token, name)
    console.print(f"deployment deleted successfully: {name}.")


def add_command(click_group):
    click_group.add_command(deployment)
