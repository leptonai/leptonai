import click
import requests
import sys
import yaml

from rich.console import Console
from rich.table import Table
from urllib.parse import urlparse

from leptonai.config import CACHE_DIR
from leptonai.util import click_group, create_header, get_full_workspace_api_url


console = Console(highlight=False)

WORKSPACE_FILE = CACHE_DIR / "workspace_info.yaml"


@click_group()
def workspace():
    pass


def _is_valid_url(candidate_str):
    parsed = urlparse(candidate_str)
    return parsed.scheme != "" and parsed.netloc != ""


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
    save_workspace(workspace_name, workspace_url, auth_token=auth_token)
    set_current_workspace(workspace_name)
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
    Login to a workspace.
    """
    if not workspace_name and not workspace_url:
        console.print("Must specify --workspace-name or --workspace-url")
        sys.exit(1)
    elif workspace_name and workspace_url:
        # Check if workspace url exists. If it doesn't, we register it.
        workspaces = load_workspace_info()["workspaces"]
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
            set_current_workspace(workspace_name)
        else:
            # This implies that, we can possibly register multiple names to the
            # same url. This is not a problem, but it won't create any conflicts
            # so we allow users to do it.
            _register_and_set(workspace_name, workspace_url, auth_token=auth_token)
    elif workspace_name:
        # Check if workspace name exists.
        workspaces = load_workspace_info()["workspaces"]
        if workspace_name in workspaces:
            workspace_url = workspaces[workspace_name]["url"]
            set_current_workspace(workspace_name)
        else:
            # New supported feature: if no workspace url is given and workspace name
            # does not exist, we register it with the automatically generated url.
            workspace_url = get_full_workspace_api_url(workspace_name)
            _register_and_set(workspace_name, workspace_url, auth_token=auth_token)
    elif workspace_url:
        if not _is_valid_url(workspace_url):
            console.print(
                f"[red]{workspace_url}[/] does not seem to be a valid URL. Please"
                " check."
            )
            sys.exit(1)
        # Check if workspace url exists.
        workspaces = load_workspace_info()["workspaces"]
        for name, workspace in workspaces.items():
            if workspace["url"] == workspace_url:
                workspace_name = name
                break
        if workspace_name:
            # if it does, log in.
            set_current_workspace(workspace_name)
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
        try:
            auth_token = get_auth_token(workspace_url)
            # TODO: change the url from /cluster to /workspace once platform has also renamed it.
            response = requests.get(
                workspace_url + "/cluster", headers=create_header(auth_token)
            )
        except Exception as e:
            console.print("[red]Cannot connect to the workspace url.[/]")
            console.print("Include the following exception message when you seek help:")
            console.print(str(e))
            sys.exit(1)
        console.print(
            f"Workspace info: build_time={response.json()['build_time']},"
            f" git_commit={response.json()['git_commit']}"
        )
    console.print(f"Workspace {workspace_name} ({workspace_url}) [green]logged in[/]")


@workspace.command()
def logout():
    """
    Log out of the current workspace.
    """
    set_current_workspace(None)
    console.print("[green]Logged out[/]")


@workspace.command()
def list():
    """
    List currently recorded workspacees.
    """
    workspace_info = load_workspace_info()
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
    Remove a workspace from the list.
    """
    if workspace_name is None:
        console.print("Must specify --workspace-name")
        sys.exit(1)
    try:
        remove_workspace(workspace_name)
        console.print(f'Workspace "{workspace_name}" [green]removed[/]')
    except KeyError:
        console.print(f'Workspace "{workspace_name}" [red]does not exist[/]')
        console.print(
            'Please use "lep workspace list" to check the name of the workspaces.'
        )
        sys.exit(1)


def add_command(cli_group):
    cli_group.add_command(workspace)


def load_workspace_info():
    workspace_info = {"workspaces": {}, "current_workspace": None}
    if WORKSPACE_FILE.exists():
        with open(WORKSPACE_FILE) as f:
            workspace_info = yaml.safe_load(f)
    return workspace_info


def save_workspace(name, url, terraform_dir=None, auth_token=None):
    workspace_info = load_workspace_info()
    workspace_info["workspaces"][name] = {}
    workspace_info["workspaces"][name]["url"] = url
    workspace_info["workspaces"][name]["terraform_dir"] = terraform_dir
    workspace_info["workspaces"][name]["auth_token"] = auth_token

    with open(WORKSPACE_FILE, "w") as f:
        yaml.safe_dump(workspace_info, f)


def remove_workspace(name):
    workspace_info = load_workspace_info()
    workspace_info["workspaces"].pop(name)
    if workspace_info["current_workspace"] == name:
        workspace_info["current_workspace"] = None
    with open(WORKSPACE_FILE, "w") as f:
        yaml.safe_dump(workspace_info, f)


def set_current_workspace(name):
    workspace_info = load_workspace_info()
    workspace_info["current_workspace"] = name
    with open(WORKSPACE_FILE, "w") as f:
        yaml.safe_dump(workspace_info, f)


def get_auth_token(workspace_url):
    #  TODO: Store current auth token in yaml for constant time access
    workspace_info = load_workspace_info()
    for _, vals in workspace_info["workspaces"].items():
        if vals["url"] == workspace_url:
            return vals["auth_token"]
    return None


def get_current_workspace_url():
    workspace_info = load_workspace_info()
    current_workspace = workspace_info["current_workspace"]
    if current_workspace is None:
        return None
    workspaces = workspace_info["workspaces"]
    return workspaces[current_workspace]["url"]


def get_workspace_url(workspace_url=None):
    if workspace_url is not None:
        return workspace_url
    return get_current_workspace_url()
