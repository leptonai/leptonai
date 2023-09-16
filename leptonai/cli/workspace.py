import click
import sys
from typing import Optional

from rich.console import Console
from rich.table import Table

from leptonai.api import workspace as api
from leptonai.api.workspace import WorkspaceInfoLocalRecord
from .util import click_group, get_connection_or_die, check, guard_api, sizeof_fmt

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
@click.option("--workspace-id", "-i", help="The workspace id to log in to.")
@click.option(
    "--auth-token", "-t", help="Authentication token for the workspace.", default=None
)
@click.option("--display-name", "-n", help="The workspace display name to log in to.")
@click.option(
    "--test-only-workspace-url",
    hidden=True,
    help="Explicit workspace url to use for internal testing purposes.",
    default=None,
)
def login(
    workspace_id: Optional[str] = None,
    auth_token: Optional[str] = None,
    display_name: Optional[str] = None,
    test_only_workspace_url: Optional[str] = None,
):
    """
    Logs in to a workspace. This also verifies that the workspace is accessible.
    """
    check(
        workspace_id or display_name, "Must specify --workspace-id or --display-name."
    )
    if workspace_id is None:
        # We will try to find the workspace id from the display name.
        workspaces = WorkspaceInfoLocalRecord.get_all_workspaces()
        matching_ids = []
        for workspace_id, info in workspaces.items():
            if info.get("display_name", None) == display_name:
                matching_ids.append(workspace_id)
        check(
            len(matching_ids) > 0,
            f"No workspace with the given display name [red]{display_name}[/]"
            " exists. Please first log in to the workspace using `lep workspace"
            " login -i <workspace-id>`.",
        )
        check(
            len(matching_ids) == 1,
            "Multiple workspaces with the given display name"
            f" [red]{display_name}[/] exists. Note that display names may not be"
            " unique - in this case, please log in with the workspace id using"
            " `lep workspace login -i <workspace-id>`.",
        )
        workspace_id = matching_ids[0]
    if test_only_workspace_url:
        check(
            workspace_id,
            "Must specify --workspace-id if using --test-only-workspace-url. This"
            " will create a new workspace login with the given workspace url. Also,"
            " you should only use this if you are running unit tests for the Lepton"
            " SDK.",
        )
        console.print("Using test-only workspace url for internal testing purposes.")
        console.print("Do not use this option unless you know what you are doing.")
        workspace_url = test_only_workspace_url
    else:
        workspace_url = None
    workspaces = WorkspaceInfoLocalRecord.get_all_workspaces()
    if workspace_id in workspaces:
        # If this workspace already exists, we will update the auth token if given.
        # Although the workspace url is actually already stored in workspaces[workspace_id]["url"],
        # it is still a good idea to re-check it in case the system updates the url.
        if auth_token:
            console.print(f"Will update info for workspace [green]{workspace_id}[/]")
            WorkspaceInfoLocalRecord.set_and_save(
                workspace_id, workspace_url, auth_token=auth_token
            )
        else:
            WorkspaceInfoLocalRecord.set_current(workspace_id)
    else:
        WorkspaceInfoLocalRecord.set_and_save(
            workspace_id, workspace_url, auth_token=auth_token
        )
    console.print(f"Workspace [green]{workspace_id}[/] logged in.")


@workspace.command()
def logout():
    """
    Log out of the current workspace. After logout, all lep commands that can
    operate both locally and remotely, such as `lep photon run`, will be carried
    out locally in default.
    """
    WorkspaceInfoLocalRecord.set_current(None)
    console.print("[green]Logged out[/]")


@workspace.command()
def list():
    """
    List current workspaces and their urls on record. For any workspace displayed
    in the list, you can log in to it by `lep workspace login -i <id>`.
    """
    workspace_info = WorkspaceInfoLocalRecord.get_all_workspaces()
    current_workspace = WorkspaceInfoLocalRecord.get_current_workspace_id()
    table = Table()
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("URL")
    table.add_column("Role")
    table.add_column("Auth Token")
    for workspace_id, info in workspace_info.items():
        url = info["url"]
        # in older versions of the SDK, "display_name" field does not exist, so we
        # add a sanity check.
        name = info.get("display_name", "")
        role = "user"
        if info["terraform_dir"] is not None:
            role = "creator"
        token = info.get("auth_token", "")
        if token:
            token = f"{token[:2]}****{token[-2:]}" if len(token) > 8 else "******"
        # Mark current workspace as green.
        if workspace_id == current_workspace:
            name = f"[green]{name}[/]"
            workspace_id = f"[green]{workspace_id}[/]"
            url = f"[green]{url}[/]"
            role = f"[green]{role}[/]"
            token = f"[green]{token}[/]"
        table.add_row(workspace_id, name, url, role, token)
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
        WorkspaceInfoLocalRecord.remove(workspace_id)
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
    current_workspace = WorkspaceInfoLocalRecord.get_current_workspace_id()
    check(
        current_workspace,
        "It seems that you are not logged in. Please run `lep workspace login` first.",
    )
    console.print(current_workspace, end="")


@workspace.command()
def token():
    """
    Prints the authentication token of the current workspace. This is useful
    when you want to obtain the workspace token in the command line in e.g.
    a shell script, but do not want to hardcode it in the source file.
    """
    token = WorkspaceInfoLocalRecord._get_current_workspace_token()
    console.print(token, end="")


@workspace.command()
def url():
    """
    Prints the url of the current workspace. This is useful when you want to
    obtain the workspace url in the command line in e.g. a shell script, but
    do not want to hardcode it in the source file.
    """
    url = WorkspaceInfoLocalRecord._get_current_workspace_deployment_url()
    check(
        url,
        "It seems that you are not logged in. Please run `lep workspace login` first.",
    )
    console.print(url, end="")


@workspace.command()
def status():
    """
    Prints the status of the current workspace.
    """
    conn = get_connection_or_die()
    info = api.get_workspace_info(conn)
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
    # Note: in our backend, right now the "workspace_name" item is actually
    # the workspace id in the frontend definition. If we decide to consolidate
    # naming, consider changing it.
    id = info["workspace_name"]

    console.print(f"id:         {id}")
    console.print(
        f"name:       {WorkspaceInfoLocalRecord._get_current_workspace_display_name()}"
    )
    console.print(f"state:      {info['workspace_state']}")
    console.print(f"build time: {info['build_time']}")
    console.print(f"version:    {info['git_commit']}")
    console.print(f"Disk Usage: {sizeof_fmt(info['workspace_disk_usage_bytes'])}")
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
