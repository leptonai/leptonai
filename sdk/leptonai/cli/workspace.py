import click
import sys
from typing import Optional

from rich.console import Console
from rich.table import Table

from leptonai.api import workspace as api
from leptonai.config import CACHE_DIR
from .util import (
    click_group,
    get_workspace_and_token_or_die,
    check,
    guard_api,
)

console = Console(highlight=False)

WORKSPACE_FILE = CACHE_DIR / "workspace_info.yaml"


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


def _register_and_set(
    workspace_id: str, workspace_url: str, auth_token: Optional[str] = None
):
    # Helper function to register the workspace url and log in. It does not check
    # duplicates - assuming that it has already been done.
    if auth_token is None:
        auth_token = (
            console.input(
                f'Please enter the authentication token for "{workspace_id}"'
                " (ENTER if none): "
            )
            or ""
        )
    api.save_workspace(workspace_id, workspace_url, auth_token=auth_token)
    api.set_current_workspace(workspace_id)
    console.print(f'Workspace "{workspace_id}" [green]registered[/].')
    console.print(
        f"Next time, you can just use `lep workspace login -i {workspace_id}` to"
        " log in."
    )


@workspace.command()
@click.option("--workspace-id", "-i", help="The workspace id to log in to.")
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
    auth_token: Optional[str],
    test_only_workspace_url: Optional[str] = None,
):
    """
    Logs in to a workspace. This also verifies that the workspace is accessible.
    """
    check(workspace_id, "Must specify --workspace-id.")
    if test_only_workspace_url:
        console.print("Using test-only workspace url for internal testing purposes.")
        console.print("Do not use this option unless you know what you are doing.")
        workspace_url = test_only_workspace_url
    else:
        workspace_url = api.get_full_workspace_api_url(workspace_id)
    check(workspace_url, f"Workspace [red]{workspace_id}[/] does not exist.")
    workspaces = api.load_workspace_info()["workspaces"]
    if workspace_id in workspaces:
        # If this workspace already exists, we will update the auth token if given.
        # Although the workspace url is actually already stored in workspaces[workspace_id]["url"],
        # it is still a good idea to re-check it in case the system updates the url.
        if auth_token:
            console.print("Updating auth token for workspace [green]{workspace_id}[/]")
            _register_and_set(workspace_id, workspace_url, auth_token=auth_token)
        api.set_current_workspace(workspace_id)
    else:
        # If workspace id does not exist, we register it.
        _register_and_set(workspace_id, workspace_url, auth_token=auth_token)
    console.print(f"Workspace [green]{workspace_id}[/] logged in.")


@workspace.command()
def logout():
    """
    Log out of the current workspace. After logout, all lep commands that can
    operate both locally and remotely, such as `lep photon run`, will be carried
    out locally in default.
    """
    api.set_current_workspace(None)
    console.print("[green]Logged out[/]")


@workspace.command()
def list():
    """
    List current workspaces and their urls on record. For any workspace displayed
    in the list, you can log in to it by `lep workspace login -i <id>`.
    """
    workspace_info = api.load_workspace_info()
    workspaces = workspace_info["workspaces"]
    current_workspace = workspace_info["current_workspace"]
    table = Table()
    table.add_column("ID")
    table.add_column("URL")
    table.add_column("Role")
    table.add_column("Auth Token")
    for workspace_id, info in workspaces.items():
        url = info["url"]
        if workspace_id == current_workspace:
            workspace_id = f'[green]{workspace_id + " (logged in)"}[/]'
            url = f"[green]{url}[/]"
        role = "user"
        if info["terraform_dir"] is not None:
            role = "creator"
        token = info.get("auth_token", "")
        if token:
            token = f"{token[:2]}***{token[-2:]}" if len(token) > 4 else "*****"
        table.add_row(workspace_id, url, role, token)
    console.print(table)


@workspace.command()
@click.option("--workspace-id", "-i", help="ID of the workspace", required=True)
def remove(workspace_id):
    """
    Remove a workspace from the record. After removal, the locally stored
    url and auth token will be deleted. If the workspace is currently logged in,
    you will be logged out.
    """
    if workspace_id is None:
        console.print("Must specify --workspace-id")
        sys.exit(1)
    try:
        api.remove_workspace(workspace_id)
        console.print(f'Workspace "{workspace_id}" [green]removed[/]')
    except KeyError:
        console.print(f'Workspace "{workspace_id}" [red]does not exist[/]')
        console.print(
            'Please use "lep workspace list" to check the ID of the workspaces.'
        )
        sys.exit(1)


@workspace.command()
def id():
    """
    Prints the id of the current workspace. This is useful when you want to
    obtain the workspace id in the command line in e.g. a shell script, but
    do not want to hardcode it in the source file.
    """
    workspace_info = api.load_workspace_info()
    current_workspace = workspace_info["current_workspace"]
    console.print(current_workspace, end="")


@workspace.command()
def token():
    """
    Prints the authentication token of the current workspace. This is useful
    when you want to obtain the workspace token in the command line in e.g.
    a shell script, but do not want to hardcode it in the source file.
    """
    _, auth_token = get_workspace_and_token_or_die()
    console.print(auth_token, end="")


@workspace.command()
def status():
    """
    Prints the status of the current workspace.
    """
    url, auth_token = get_workspace_and_token_or_die()
    info = api.get_workspace_info(url, auth_token)
    guard_api(
        info,
        detail=True,
        msg=(
            "Cannot properly obtain info for the current workspace."
            " This should usually not happen - it might be a transient"
            " network issue. If you encounter this persistently, please"
            " contact us by sharing the error message above."
        ),
    )
    console.print(f"name:       {info['workspace_name']}")
    console.print(f"build time: {info['build_time']}")
    console.print(f"version:    {info['git_commit']}")
    console.print("quota usage:")
    quota = info["resource_quota"]
    quota_limit = quota["limit"]
    quota_used = quota["used"]
    table = Table()
    table.add_column("Resource")
    table.add_column("Limit")
    table.add_column("Used")
    table.add_row("cpu (cores)", str(quota_limit["cpu"]), str(quota_used["cpu"]))
    table.add_row("memory (MiB)", str(quota_limit["memory"]), str(quota_used["memory"]))
    table.add_row(
        "gpu (cards)",
        str(quota_limit["accelerator_num"]),
        str(quota_used["accelerator_num"]),
    )
    console.print(table)


def add_command(cli_group):
    cli_group.add_command(workspace)
