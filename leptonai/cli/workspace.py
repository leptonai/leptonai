from datetime import datetime

import click
import sys
from typing import Optional

from rich.console import Console
from rich.table import Table

from leptonai.config import WORKSPACE_API_PATH
from leptonai.api.v1.workspace_record import WorkspaceRecord
from .util import click_group, check, sizeof_fmt
from ..api.v1.utils import WorkspaceNotFoundError, WorkspaceUnauthorizedError

console = Console(highlight=False)


@click_group()
def workspace():
    """
    Manage workspace access to the Lepton AI cloud.

    Workspace is the place you perform daily operation with photons, deployments,
    storage, and other resources.

    The workspace commands allow you to log in and out of multiple workspaces,
    and keeps track of the workspace credentials you are currently working on.
    """
    pass


@workspace.command()
@click.option(
    "--workspace-id", "-i", help="The workspace id to log in to.", default=None
)
@click.option(
    "--auth-token", "-t", help="Authentication token for the workspace.", default=None
)
@click.option(
    "--test-only-workspace-url",
    hidden=True,
    help="Explicit workspace url to use for internal testing purposes.",
    default=None,
)
def login(
    workspace_id: str,
    auth_token: Optional[str] = None,
    test_only_workspace_url: Optional[str] = None,
):
    """
    Logs in to a workspace. This also verifies that the workspace is accessible.
    """
    if workspace_id is None:
        # If workspace_id is not given and current workspace is present, we will
        # simply print the info.
        if WorkspaceRecord.current():
            pass
    elif WorkspaceRecord.has(workspace_id):
        # already has the info: update the auth token if given.
        info = WorkspaceRecord.get(workspace_id)
        if auth_token or test_only_workspace_url:
            WorkspaceRecord.set_or_exit(
                workspace_id, auth_token=auth_token, url=test_only_workspace_url
            )
        else:
            WorkspaceRecord.set_or_exit(workspace_id, auth_token=info.auth_token, url=info.url)  # type: ignore
    else:
        WorkspaceRecord.set_or_exit(
            workspace_id, auth_token=auth_token, url=test_only_workspace_url
        )
    # Try to login and print the info.
    api_client = WorkspaceRecord.client()
    try:
        info = api_client.info()

        console.print(f"Logged in to your workspace [green]{info.workspace_name}[/].")
        console.print(f"\t      tier: {info.workspace_tier}")
        console.print(f"\tbuild time: {info.build_time}")
        console.print(f"\t   version: {api_client.version()}")
    except WorkspaceUnauthorizedError as e:
        console.print("\n", e)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        console.print(f"""
        [red bold]Invalid Workspace Access Detected[/]
        [red]Workspace ID:[/red] {e.workspace_id}

        [bold]To resolve this issue:[/bold]
        1. [yellow]Please check the login info you just used above[/yellow]
        2. [yellow]Login to the workspace with valid credentials:[/yellow]
           [green]lep workspace login -i <valid_workspace_id> -t <valid_workspace_token>[/green]
        3. [green]If the workspace was just created, please wait for 5 - 10 minutes. [/green]
           [yellow]Contact us if the workspace remains unavailable after 10 minutes.[/yellow]
           (Current Time: [bold blue]{current_time}[/bold blue])
        """)

    except WorkspaceNotFoundError as e:
        console.print("\n", e)

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        console.print(f"""
        [red bold]Workspace Not Found[/]
        [red]Workspace ID:[/red] {e.workspace_id}

        [bold]To resolve this issue:[/bold]
        1. [green]If the workspace was just created, please wait for 10 minutes. [/green]
           [yellow]Contact us if the workspace remains unavailable after 10 minutes.[/yellow]
           (Current Time: [bold blue]{current_time}[/bold blue])
        2. [green]Please check the login info you just used above[/green]
        3. [yellow]Login to the workspace with valid credentials:[/yellow]
           [green]lep workspace login -i <valid_workspace_id> -t <valid_workspace_token>[/green]
        """)


@workspace.command()
@click.option(
    "--purge", is_flag=True, help="Purge the credentials of the lepton login info."
)
def logout(purge):
    """
    Logout of the Lepton AI cloud.
    """
    WorkspaceRecord.logout(purge=purge)
    console.print("[green]Logged out[/]")


@workspace.command(name="list")
def list_command():
    """
    List current workspaces and their urls on record. For any workspace displayed
    in the list, you can log in to it by `lep workspace login -i <id>`.
    """
    workspace_list = WorkspaceRecord.workspaces()
    current_workspace = WorkspaceRecord.current()
    table = Table()
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("URL")
    table.add_column("Auth Token")
    for info in workspace_list:
        table.add_row(
            info.id_,
            info.display_name,
            info.url,
            (
                info.auth_token[:2] + "****" + info.auth_token[-2:]
                if info.auth_token
                else ""
            ),
        )
    if current_workspace:
        console.print(f"Current workspace: [green]{current_workspace.id_}[/]")
    console.print("All workspaces:")
    console.print(table)


@workspace.command()
@click.option("--workspace-id", "-i", help="ID of the workspace", required=True)
def remove(workspace_id: str):
    """
    Remove a workspace from the record. After removal, the locally stored
    url and auth token will be deleted. If the workspace is currently logged in,
    you will be logged out.
    """
    if not WorkspaceRecord.has(workspace_id):
        console.print(f"Workspace not exist: [red]{workspace_id}.[/]")
        return
    WorkspaceRecord.remove(workspace_id)
    console.print(f"Successfully removed workspace: [green]{workspace_id}.[/]")


@workspace.command()
def removeall():
    """
    Remove all workspaces.
    """
    workspace_list = WorkspaceRecord.workspaces()
    for info in workspace_list:
        WorkspaceRecord.remove(info.id_)
        console.print(f"Successfully removed workspace: [green]{info.id_}.[/]")


@workspace.command()
def id():
    """
    Prints the id of the current workspace. This is useful when you want to
    obtain the workspace id in the command line in e.g. a shell script, but
    do not want to hardcode it in the source file.
    """
    current = WorkspaceRecord.current()
    check(
        current,
        "It seems that you are not logged in. Please run `lep login` first.",
    )
    console.print(current.id_, end="")  # type: ignore


@workspace.command()
def token():
    """
    Prints the authentication token of the current workspace. This is useful
    when you want to obtain the workspace token in the command line in e.g.
    a shell script, but do not want to hardcode it in the source file.
    """
    current = WorkspaceRecord.current()
    check(
        current,
        "It seems that you are not logged in. Please run `lep login` first.",
    )
    console.print(current.auth_token, end="")  # type: ignore


@workspace.command()
def url():
    """
    Prints the url of the current workspace. This is useful when you want to
    obtain the workspace url in the command line in e.g. a shell script, but
    do not want to hardcode it in the source file.
    """
    current = WorkspaceRecord.current()
    check(
        current,
        "It seems that you are not logged in. Please run `lep login` first.",
    )
    url = current.url
    if current.url.endswith(WORKSPACE_API_PATH):
        url = current.url[: -len(WORKSPACE_API_PATH)]
        console.print(url, end="")
    else:
        console.print(
            "Local info and server info mismatch. Please report this to us with the"
            " following debug info:"
        )
        console.print(f"debug url: {current.url}")
        sys.exit(1)


@workspace.command()
def status():
    """
    Prints the status of the current workspace.
    """
    api_client = WorkspaceRecord.client()
    info = api_client.info()
    console.print(f"id:          {info.workspace_name}")
    console.print(f"state:       {info.workspace_state}")
    console.print(f"tier:        {info.workspace_tier}")
    console.print(f"build time:  {info.build_time}")
    console.print(f"version:     {info.git_commit}")
    console.print(f"disk usage:  {sizeof_fmt(info.workspace_disk_usage_bytes)}")
    console.print(f"photons:     {info.workloads.num_photons}")
    console.print(f"deployments: {info.workloads.num_deployments}")
    console.print(f"jobs:        {info.workloads.num_jobs}")
    console.print(f"pods:        {info.workloads.num_pods}")
    console.print(f"secrets:     {info.workloads.num_secrets}")

    console.print("quota usage:")
    quota = info.resource_quota
    quota_limit = quota.limit
    quota_used = quota.used
    table = Table()
    table.add_column("Resource")
    table.add_column("Limit")
    table.add_column("Used")
    table.add_row("cpu (cores)", str(quota_limit.cpu), str(quota_used.cpu))
    table.add_row("memory (MiB)", str(quota_limit.memory), str(quota_used.memory))
    table.add_row(
        "gpu (cards)",
        str(quota_limit.accelerator_num),
        str(quota_used.accelerator_num),
    )
    console.print(table)


def add_command(cli_group):
    cli_group.add_command(workspace)
