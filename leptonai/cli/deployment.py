from datetime import datetime
import sys

import click
from rich.table import Table

from .util import (
    console,
    click_group,
    guard_api,
    get_workspace_and_token_or_die,
    explain_response,
)
from leptonai.api import deployment as api


@click_group()
def deployment():
    pass


@deployment.command()
def create():
    """
    A wrapper function to simply notify the user that they should use `lep photon run` instead.
    """
    console.print("Please use `lep photon run` instead.")
    sys.exit(1)


@deployment.command()
def list():
    """
    Lists all deployments in the current workspace.
    """
    workspace_url, auth_token = get_workspace_and_token_or_die()
    deployments = guard_api(
        api.list_deployment(workspace_url, auth_token),
        detail=True,
        msg="Cannot list deployments. See error message above.",
    )
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
            status["endpoint"]["external_endpoint"],
        )
    console.print(table)
    return 0


@deployment.command()
@click.option("--name", "-n", help="deployment name")
def remove(name):
    """
    Removes a deployment of the given name.
    """
    workspace_url, auth_token = get_workspace_and_token_or_die()
    response = api.remove_deployment(workspace_url, auth_token, name)
    explain_response(
        response,
        f"Deployment [green]{name}[/] removed.",
        f"Deployment [yellow]{name}[/] does not exist.",
        (
            f"{response.text}\nFailed to remove deployment [red]{name}[/]. See error"
            " message above."
        ),
    )
    return 0


def add_command(cli_group):
    cli_group.add_command(deployment)
