import click
import sys
import yaml

from rich.console import Console
from rich.table import Table
from urllib.parse import urlparse

from leptonai.config import CACHE_DIR


console = Console(highlight=False)

CLUSTER_FILE = CACHE_DIR / "cluster_info.yaml"


@click.group()
def remote():
    pass


def _is_valid_url(candidate_str):
    parsed = urlparse(candidate_str)
    return parsed.scheme != "" and parsed.netloc != ""


def _register_and_login(remote_name, remote_url, auth_token=None):
    # Helper function to register the remote url and log in. It does not check
    # duplicates - assuming that it has already been done.
    if auth_token is None:
        auth_token = (
            console.input(
                f'Please enter the authentication token for "{remote_name}"'
                " (ENTER if none): "
            )
            or ""
        )
    save_cluster(remote_name, remote_url, auth_token=auth_token)
    set_current_cluster(remote_name)
    console.print(f'Cluster "{remote_url}" [green]registered and logged in[/]')
    console.print(
        f"Next time, you can just use `lep remote login -n {remote_name}` to log in."
    )


@remote.command()
@click.option("--remote-name", "-n", help="Name of the remote cluster")
@click.option("--remote-url", "-r", help="URL of the remote cluster")
@click.option("--auth-token", "-t", help="Authentication token for the remote cluster")
def login(remote_name, remote_url, auth_token):
    """
    Login to a remote cluster.
    """
    if not remote_name and not remote_url:
        console.print("Must specify --remote-name or --remote-url")
        sys.exit(1)
    elif remote_name and remote_url:
        # Check if remote url exists. If it doesn't, we register it.
        clusters = load_cluster_info()["clusters"]
        if remote_name in clusters and clusters[remote_name]["url"] != remote_url:
            console.print(
                f'[red]Cluster "{remote_name}" already registered[/] but not matching'
                f' {remote_url}.Got {clusters[remote_name]["url"]} instead. Please'
                " double check your input."
            )
            sys.exit(1)
        registered_name = None
        for name, cluster in clusters.items():
            if cluster["url"] == remote_url:
                registered_name = name
                break
        if registered_name == remote_name:
            set_current_cluster(remote_name)
            console.print(f'Cluster "{remote_name}" [green]logged in[/]')
            return
        else:
            # This implies that, we can possibly register multiple names to the
            # same url. This is not a problem, but it won't create any conflicts
            # so we allow users to do it.
            _register_and_login(remote_name, remote_url, auth_token=auth_token)
            return
    elif remote_name:
        # Check if remote name exists.
        clusters = load_cluster_info()["clusters"]
        if remote_name in clusters:
            remote_url = clusters[remote_name]["url"]
            set_current_cluster(remote_name)
            console.print(f'Cluster "{remote_name}" [green]logged in[/]')
            return
        else:
            console.print(
                f'[red]Cluster "{remote_name}" does not exist[/]. Please check your'
                " name, or use `lep remote login -r [url]` to register a new remote"
                " cluster."
            )
            sys.exit(1)
    elif remote_url:
        if not _is_valid_url(remote_url):
            console.print(
                f"[red]{remote_url}[/] does not seem to be a valid URL. Please check."
            )
            sys.exit(1)
        # Check if remote url exists.
        clusters = load_cluster_info()["clusters"]
        for name, cluster in clusters.items():
            if cluster["url"] == remote_url:
                remote_name = name
                break
        if remote_name is not None:
            # if it does, log in.
            set_current_cluster(remote_name)
            console.print(
                f'"{remote_url}" already registered with display name'
                f" [green]{remote_name}[/]."
            )
            console.print(
                f"Next time, you can just use `lep remote login -n {remote_name}` to"
                " log in."
            )
            console.print(f'Cluster "{remote_url}" [green]logged in[/]')
            return
        else:
            console.print(f"Adding a new remote cluster {remote_url}.")
            while remote_name is None:
                remote_name = console.input(
                    "Please give the remote cluster a display name (eg. my-remote):"
                )
                if not remote_name:
                    console.print("Remote cluster name cannot be empty.")
            _register_and_login(remote_name, remote_url, auth_token=auth_token)
            return


@remote.command()
def logout():
    set_current_cluster(None)
    console.print("[green]Logged out[/]")


@remote.command()
def list():
    cluster_info = load_cluster_info()
    clusters = cluster_info["clusters"]
    current_cluster = cluster_info["current_cluster"]
    table = Table()
    table.add_column("Name")
    table.add_column("URL")
    table.add_column("Role")
    table.add_column("Auth Token")
    for name, info in clusters.items():
        url = info["url"]
        if name == current_cluster:
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


@remote.command()
@click.option("--remote-name", "-n", help="Name of the remote cluster", required=True)
def remove(remote_name):
    if remote_name is None:
        console.print("Must specify --remote-name")
        sys.exit(1)
    try:
        remove_cluster(remote_name)
        console.print(f'Cluster "{remote_name}" [green]removed[/]')
    except KeyError:
        console.print(f'Cluster "{remote_name}" [red]does not exist[/]')
        console.print(
            'Please use "lep remote list" to check the name of the remote clusters.'
        )
        sys.exit(1)


def add_command(click_group):
    click_group.add_command(remote)


def load_cluster_info():
    cluster_info = {"clusters": {}, "current_cluster": None}
    if CLUSTER_FILE.exists():
        with open(CLUSTER_FILE) as f:
            cluster_info = yaml.safe_load(f)
    return cluster_info


def save_cluster(name, url, terraform_dir=None, auth_token=None):
    cluster_info = load_cluster_info()
    cluster_info["clusters"][name] = {}
    cluster_info["clusters"][name]["url"] = url
    cluster_info["clusters"][name]["terraform_dir"] = terraform_dir
    cluster_info["clusters"][name]["auth_token"] = auth_token

    with open(CLUSTER_FILE, "w") as f:
        yaml.safe_dump(cluster_info, f)


def remove_cluster(name):
    cluster_info = load_cluster_info()
    cluster_info["clusters"].pop(name)
    if cluster_info["current_cluster"] == name:
        cluster_info["current_cluster"] = None
    with open(CLUSTER_FILE, "w") as f:
        yaml.safe_dump(cluster_info, f)


def set_current_cluster(name):
    cluster_info = load_cluster_info()
    cluster_info["current_cluster"] = name
    with open(CLUSTER_FILE, "w") as f:
        yaml.safe_dump(cluster_info, f)


def get_auth_token(remote_url):
    #  TODO: Store current auth token in yaml for constant time access
    cluster_info = load_cluster_info()
    for _, vals in cluster_info["clusters"].items():
        if vals["url"] == remote_url:
            return vals["auth_token"]
    return None


def get_current_cluster_url():
    cluster_info = load_cluster_info()
    current_cluster = cluster_info["current_cluster"]
    if current_cluster is None:
        return None
    clusters = cluster_info["clusters"]
    return clusters[current_cluster]["url"]


def get_remote_url(remote_url=None):
    if remote_url is not None:
        return remote_url
    return get_current_cluster_url()
