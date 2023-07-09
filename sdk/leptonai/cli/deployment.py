from datetime import datetime

import click
from rich.table import Table

from .util import (
    console,
    check,
    click_group,
    guard_api,
    get_workspace_and_token_or_die,
    explain_response,
)
from leptonai.api import deployment as api


@click_group()
def deployment():
    """
    Manage deployments on the Lepton AI cloud.

    Deployment is a running instance of a photon. Deployments are created using
    the `lep photon run` command. Usually, a deployment exposes one or more HTTP
    endpoints that the users call, either via a RESTful API, or a python client
    defined in `leptonai.client`.

    The deployment commands allow you to list and remove deployments on the
    Lepton AI cloud.
    """
    pass


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
    Removes a deployment.
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


@deployment.command()
@click.option("--name", "-n", help="deployment name")
def status(name):
    """
    Gets the status of a deployment.
    """
    check(name, "Deployment name not specified. Use `lep deployment status -n <name>`.")
    workspace_url, auth_token = get_workspace_and_token_or_die()
    info = guard_api(
        api.get_readiness(workspace_url, auth_token, name),
        detail=True,
        msg=f"Cannot obtain status info for [red]{name}[/]. See error above.",
    )
    # Print a table of readiness information.
    table = Table(title=f"Deployment [green]{name}[/] status", show_lines=True)
    table.add_column("replica id")
    table.add_column("status")
    table.add_column("message")
    ready_count = 0
    for id, value in info.items():
        reason = value[0]["reason"]
        message = value[0]["message"]
        # Do we need to display red?
        if reason == "Ready":
            reason = f"[green]{reason}[/]"
            ready_count += 1
        else:
            reason = f"[yellow]{reason}[/]"
        if message == "":
            message = "(empty)"
        table.add_row(id, reason, message)
    console.print(table)
    console.print(f"[green]{ready_count}[/] out of {len(info)} replicas ready.")


@deployment.command()
@click.option("--name", "-n", help="deployment name")
@click.option("--replica", "-r", help="replica name", default=None)
def log(name, replica):
    """
    Gets the log of a deployment.
    """
    check(name, "Deployment name not specified.")
    workspace_url, auth_token = get_workspace_and_token_or_die()
    if not replica:
        # obtain replica information, and then select the first one.
        console.print(
            f"Replica name not specified for [yellow]{name}[/]. Selecting the first"
            " replica."
        )
        replicas = guard_api(
            api.get_replicas(workspace_url, auth_token, name),
            detail=True,
            msg=f"Cannot obtain replica info for [red]{name}[/]. See error above.",
        )
        check(len(replicas) > 0, f"No replicas found for [red]{name}[/].")
        replica = replicas[0]["id"]
        console.print(f"Selected replica [green]{replica}[/].")
    else:
        console.print(f"Showing log for replica [green]{replica}[/].")
    stream_or_err = guard_api(
        api.get_log(workspace_url, auth_token, name, replica),
        detail=False,
        msg="Cannot obtain log for [red]{replica}[/]. See error above.",
    )
    # Print the log as a continuous stream until the user presses Ctrl-C.
    try:
        for chunk in stream_or_err:
            console.print(chunk, end="")
    except KeyboardInterrupt:
        console.print("Disconnected.")
    except Exception:
        console.print("Connection stopped.")
        return


@deployment.command()
@click.option("--name", "-n", help="deployment name")
@click.option("--replica", "-r", help="number of replicas", type=int, default=None)
def update(name, replica):
    """
    Updates a deployment. Currently, only adjustment of the
    number of replicas is supported.
    """
    check(replica is not None, "Number of replicas not specified.")
    check(replica > 0, f"Invalid number of replicas: {replica}")
    # Just to avoid stupid errors right now, we will limit the number of replicas
    # to 100 for now.
    check(replica <= 100, f"Invalid number of replicas: {replica}")
    workspace_url, auth_token = get_workspace_and_token_or_die()
    guard_api(
        api.update_deployment(workspace_url, auth_token, name, replica),
        detail=True,
        msg=f"Cannot update deployment [red]{name}[/]. See error above.",
    )
    console.print(
        f"Deployment [green]{name}[/] updated to replica=[green]{replica}[/]."
    )


def add_command(cli_group):
    cli_group.add_command(deployment)
