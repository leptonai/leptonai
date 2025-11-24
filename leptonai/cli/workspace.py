from datetime import datetime

import click
import sys
from typing import Optional

from loguru import logger
from rich.console import Console
from rich.table import Table

from leptonai.api.v2.workspace_record import WorkspaceRecord
from .util import click_group, check, sizeof_fmt
from ..api.v2.utils import WorkspaceNotFoundError, WorkspaceUnauthorizedError

console = Console(highlight=False)


@click_group()
def workspace():
    """
    Manage workspace access to the DGX Cloud Lepton.

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
    "--workspace-url",
    hidden=True,
    help="Explicit workspace url to use for internal testing purposes.",
    default=None,
)
@click.option(
    "--lepton-classic",
    is_flag=True,
    help="Login to the classic Lepton AI workspace.",
)
@click.option(
    "--workspace-origin-url",
    help=(
        "Internal option for setting the Origin header in API calls. Used for workspace"
        " API configuration."
    ),
    hidden=True,
    default=None,
)
def login(
    workspace_id: str,
    auth_token: Optional[str] = None,
    workspace_url: Optional[str] = None,
    lepton_classic: bool = False,
    workspace_origin_url: Optional[str] = None,
):
    """
    Logs in to a workspace. This also verifies that the workspace is accessible.
    """
    if workspace_id is None:
        # If workspace_id is not given and current workspace is present, we will
        # simply print the info.
        if auth_token or workspace_url or workspace_origin_url or lepton_classic:
            console.print(
                "\n[bold red]Invalid usage:[/bold red] --auth-token,"
                " --workspace-url,"
                " --workspace-origin-url, and --lepton-classic must be used together"
                " with --workspace-id.\n[white]Either provide workspace id or remove"
                " these options to avoid misconfiguring local"
                " workspaces.[/white]\n[yellow]Example:[/yellow] [#76B900]lep workspace"
                " login -i <workspace_id> [--auth-token <auth_token>]"
                " [--workspace-url <url>]"
                " [--workspace-origin-url <url>] [--lepton-classic][/]\n"
            )
            sys.exit(1)
        if WorkspaceRecord.current():
            pass
    elif WorkspaceRecord.has(workspace_id):
        # already has the info: update the auth token if given.
        info = WorkspaceRecord.get(workspace_id)
        if auth_token or workspace_url or workspace_origin_url:
            WorkspaceRecord.set_or_exit(
                workspace_id,
                auth_token=auth_token,
                url=workspace_url,
                workspace_origin_url=workspace_origin_url,
                could_be_new_token=True,
            )
        else:
            WorkspaceRecord.set_or_exit(workspace_id, auth_token=info.auth_token, url=info.url, workspace_origin_url=info.workspace_origin_url, is_lepton_classic=lepton_classic)  # type: ignore
    else:
        if not auth_token:
            console.print(
                f"[red]Error[/]: Workspace '{workspace_id}' not found; please provide"
                " --auth-token."
            )
            sys.exit(1)

        WorkspaceRecord.set_or_exit(
            workspace_id,
            auth_token=auth_token,
            url=workspace_url,
            workspace_origin_url=workspace_origin_url,
            is_lepton_classic=lepton_classic,
            could_be_new_token=True,
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
        sys.exit(1)

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
        sys.exit(1)


@workspace.command()
@click.option(
    "--purge", is_flag=True, help="Purge the credentials of the lepton login info."
)
def logout(purge):
    """
    Logout of the DGX Cloud Lepton.
    """
    try:
        WorkspaceRecord.logout(purge=purge)
        console.print("[green]Logged out[/]")
    except RuntimeError as e:
        console.print(f"[yellow]{e}[/]")


@workspace.command(name="list")
@click.option("--debug", is_flag=True, help="Debug mode", hidden=True)
def list_command(debug):
    """
    List current workspaces and their urls on record. For any workspace displayed
    in the list, you can log in to it by `lep workspace login -i <id>`.
    """
    workspace_list = WorkspaceRecord.workspaces()
    current_workspace = WorkspaceRecord.current()
    table = Table(show_lines=True)
    table.add_column("Name / ID")
    table.add_column("URL")
    table.add_column("Auth Token")
    table.add_column("Expires")
    if debug:
        table.add_column("Origin URL")
        table.add_column("Lepton classic")
    for info in workspace_list:
        name_text = info.display_name or ""
        id_text = info.id_ or ""
        dashboard_url = WorkspaceRecord.get_dashboard_base_url(info.id_)
        if current_workspace and info.id_ == current_workspace.id_:
            name_line = f"[green]{name_text or '-'}[/]"
        else:
            name_line = name_text if name_text else "-"
        id_line_plain = f"[bright_black]{id_text}[/]" if id_text else "-"
        id_line = (
            f"[link={dashboard_url}]{id_line_plain}[/link]"
            if id_text and dashboard_url
            else id_line_plain
        )
        name_id_cell = f"{name_line}\n{id_line}"
        # Build masked token
        token_cell = (
            info.auth_token[:2] + "****" + info.auth_token[-2:]
            if info.auth_token
            else ""
        )
        # Build expires cell
        expires_cell = "-"
        # If missing, try to refresh once from server
        if getattr(info, "token_expires_at", None) is None:
            logger.trace(f"Refreshing token expires at for workspace {info.id_}")
            info.token_expires_at = WorkspaceRecord.refresh_token_expires_at(info.id_)
        if getattr(info, "token_expires_at", None):
            try:
                expires_dt = datetime.fromtimestamp(info.token_expires_at / 1000)
                total_sec = (expires_dt - datetime.now()).total_seconds()
                if total_sec < 0:
                    expires_cell = "[red]expired[/]"
                else:
                    days_left = int((total_sec + 86399) // 86400)
                    if days_left == 0:
                        expires_cell = "[red]<1 day left[/]"
                    elif days_left < 10:
                        expires_cell = f"[yellow]{days_left} days left[/]"
                    elif days_left >= 30:
                        expires_cell = f"[green]{days_left} days left[/]"
                    else:
                        expires_cell = f"{days_left} days left"
            except Exception:
                expires_cell = "-"

        row_data = [
            name_id_cell,
            info.url,
            token_cell,
            expires_cell,
        ]
        if debug:
            row_data.extend([
                info.workspace_origin_url,
                str(info.is_lepton_classic),
            ])
        table.add_row(*row_data)
    if current_workspace:
        console.print(f"Current workspace: [green]{current_workspace.id_}[/]")
    table.title = "Workspaces"
    console.print(table)
    console.print(
        "\n[bright_black]Hint[/]: 'Expires' shows the token expiration. If the token is"
        " expired or close to expiring, please re-issue a new token in the dashboard"
        " and run `lep login -c <workspace_id>:<new_token>`"
        " again.\n[bright_black]Note[/]: token expiration is available only for DGXC"
        " workspaces. If no expiration info is shown, the token may already be expired."
    )


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
    console.print(current.url)


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
