import click
import sys

from rich.console import Console
from rich.table import Table

from leptonai.api import workspace as api
from leptonai.config import CACHE_DIR
from leptonai.util import get_full_workspace_api_url
from .util import (
    click_group,
    is_valid_url,
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


def _register_and_set(workspace_name, workspace_url, auth_token=None):
    # Helper function to register the workspace url and log in. It does not check
    # duplicates - assuming that it has already been done.
    if workspace_url is None:
        console.print("You hit a programming error: no workspace URL given.")
        sys.exit(1)
    while workspace_name is None:
        workspace_name = console.input(
            "Please give the workspace a display name (eg. my-workspace):"
        )
        if not workspace_name:
            console.print("Workspace name cannot be empty.")
    if auth_token is None:
        auth_token = (
            console.input(
                f'Please enter the authentication token for "{workspace_name}"'
                " (ENTER if none): "
            )
            or ""
        )
    api.save_workspace(workspace_name, workspace_url, auth_token=auth_token)
    api.set_current_workspace(workspace_name)
    console.print(f'Workspace "{workspace_url}" [green]registered[/].')
    console.print(
        f"Next time, you can just use `lep workspace login -n {workspace_name}` to"
        " log in."
    )


@workspace.command()
@click.option("--workspace-name", "-n", help="Name of the workspace")
@click.option("--workspace-url", "-r", help="URL of the workspace")
@click.option("--auth-token", "-t", help="Authentication token for the workspace")
@click.option(
    "--dry-run",
    "-d",
    is_flag=True,
    help=(
        "[Test use only] if specified, do not attempt to verify if we can log in to the"
        " workspace. This is only used in testing."
    ),
    hidden=True,
)
def login(workspace_name, workspace_url, auth_token, dry_run):
    """
    Logs in to a workspace. This also verifies that the workspace is accessible.

    There are multiple ways to log in to a workspace, but the easiest way is to
    log in via `--workspace-name`. If you are running an enterprise version of
    Lepton AI cloud, you can log in by explicitly passing in the API server url
    via `--workspace-url`, and give it a local display name for future ease.
    """
    if not workspace_name and not workspace_url:
        console.print("Must specify --workspace-name or --workspace-url")
        sys.exit(1)
    elif workspace_name and workspace_url:
        # Check if workspace url exists. If it doesn't, we register it.
        workspaces = api.load_workspace_info()["workspaces"]
        if (
            workspace_name in workspaces
            and workspaces[workspace_name]["url"] != workspace_url
        ):
            console.print(
                f'[red]Workspace "{workspace_name}" already registered[/] but not'
                f" matching {workspace_url}.Got"
                f' {workspaces[workspace_name]["url"]} instead. Please double check'
                " your input."
            )
            sys.exit(1)
        registered_name = None
        for name, workspace in workspaces.items():
            if workspace["url"] == workspace_url:
                registered_name = name
                break
        if registered_name == workspace_name:
            api.set_current_workspace(workspace_name)
        else:
            # This implies that, we can possibly register multiple names to the
            # same url. This is not a problem, but it won't create any conflicts
            # so we allow users to do it.
            _register_and_set(workspace_name, workspace_url, auth_token=auth_token)
    elif workspace_name:
        # Check if workspace name exists.
        workspaces = api.load_workspace_info()["workspaces"]
        if workspace_name in workspaces:
            workspace_url = workspaces[workspace_name]["url"]
            api.set_current_workspace(workspace_name)
        else:
            # New supported feature: if no workspace url is given and workspace name
            # does not exist, we register it with the automatically generated url.
            workspace_url = get_full_workspace_api_url(workspace_name)
            _register_and_set(workspace_name, workspace_url, auth_token=auth_token)
    elif workspace_url:
        if not is_valid_url(workspace_url):
            console.print(
                f"[red]{workspace_url}[/] does not seem to be a valid URL. Please"
                " check."
            )
            sys.exit(1)
        # Check if workspace url exists.
        workspaces = api.load_workspace_info()["workspaces"]
        for name, workspace in workspaces.items():
            if workspace["url"] == workspace_url:
                workspace_name = name
                break
        if workspace_name:
            # if it does, log in.
            api.set_current_workspace(workspace_name)
            console.print(
                f'"{workspace_url}" already registered with display name'
                f" [green]{workspace_name}[/]."
            )
            console.print(
                f"Next time, you can just use `lep workspace login -n {workspace_name}`"
                " to log in."
            )
        else:
            console.print(f"Adding a new workspace {workspace_url}.")
            _register_and_set(workspace_name, workspace_url, auth_token=auth_token)
    # If all above logic has passed, we will have a workspace_name and workspace_url
    # at this point that we can use to log in.
    if not dry_run:
        # do sanity checks.
        url, auth_token = get_workspace_and_token_or_die()
        check(
            workspace_url == url,
            "You have encountered a programming error: workspace url mismatch."
            " Please report an issue.",
        )
        workspace_info = guard_api(
            api.get_workspace_info(workspace_url, auth_token),
            detail=True,
            msg=(
                f"Cannot properly log into workspace [red]{workspace_name}. See error"
                " message above."
            ),
        )
        console.print(
            f"Workspace info: build_time={workspace_info['build_time']},"
            f" git_commit={workspace_info['git_commit']}"
        )
    console.print(f"Workspace [green]{workspace_name}[/] ({workspace_url}) logged in.")


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
    in the list, you can log in to it by `lep workspace login -n <Name>`.
    """
    workspace_info = api.load_workspace_info()
    workspaces = workspace_info["workspaces"]
    current_workspace = workspace_info["current_workspace"]
    table = Table()
    table.add_column("Name")
    table.add_column("URL")
    table.add_column("Role")
    table.add_column("Auth Token")
    for name, info in workspaces.items():
        url = info["url"]
        if name == current_workspace:
            name = f'[green]{name + " (logged in)"}[/]'
            url = f"[green]{url}[/]"
        role = "user"
        if info["terraform_dir"] is not None:
            role = "creator"
        token = info.get("auth_token", "")
        if token:
            token = f"{token[:2]}***{token[-2:]}" if len(token) > 4 else "*****"
        table.add_row(name, url, role, token)
    console.print(table)


@workspace.command()
@click.option("--workspace-name", "-n", help="Name of the workspace", required=True)
def remove(workspace_name):
    """
    Remove a workspace from the record. After removal, the locally stored
    url and auth token will be deleted. If the workspace is currently logged in,
    you will be logged out.
    """
    if workspace_name is None:
        console.print("Must specify --workspace-name")
        sys.exit(1)
    try:
        api.remove_workspace(workspace_name)
        console.print(f'Workspace "{workspace_name}" [green]removed[/]')
    except KeyError:
        console.print(f'Workspace "{workspace_name}" [red]does not exist[/]')
        console.print(
            'Please use "lep workspace list" to check the name of the workspaces.'
        )
        sys.exit(1)


def add_command(cli_group):
    cli_group.add_command(workspace)
