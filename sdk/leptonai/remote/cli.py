import click
import yaml
import sys

from rich.console import Console
from rich.table import Table

from leptonai.config import CACHE_DIR


console = Console(highlight=False)

CLUSTER_FILE = CACHE_DIR / "cluster_info.yaml"


@click.group()
def remote():
    pass


@remote.command()
@click.option("--remote-name", "-n", help="Name of the remote cluster")
@click.option("--remote-url", "-r", help="URL of the remote cluster")
@click.option("--auth-token", "-t", help="Authentication token for the remote cluster")
def login(remote_name, remote_url, auth_token):
    if remote_name and remote_url:
        if auth_token is None:
            auth_token = (
                console.input(
                    f'Please enter the authentication token for "{remote_name}" (ENTER'
                    " if none): "
                )
                or ""
            )
        save_cluster(remote_name, remote_url, auth_token=auth_token)
        set_current_cluster(remote_name)

        console.print(f'Cluster "{remote_name}" [green]logged in[/]')
        return

    clusters = load_cluster_info()["clusters"]
    if remote_name is not None:
        remote_cluster = clusters.get(remote_name)

        if remote_cluster is None:
            console.print(f'Cluster "{remote_name}" [red]does not exist[/]')
            console.print(
                'Please use "lep remote login -r <URL>" to add the remote cluster first'
            )
            sys.exit(1)
        set_current_cluster(remote_name)

        console.print(f'Cluster "{remote_name}" [green]logged in[/]')
        return

    if remote_url is not None:
        remote_name = None
        while not remote_name:
            remote_name = console.input("Please name the remote (eg. my-remote):")
            if not remote_name:
                console.print("Remote cluster name cannot be empty")

        if auth_token is None:
            auth_token = console.input("Please enter the authentication token:") or ""
        save_cluster(remote_name, remote_url, auth_token=auth_token)
        set_current_cluster(remote_name)

        console.print(f'Cluster "{remote_name}" [green]logged in[/]')
        return

    console.print("Must specify --remote-name or --remote-url")
    sys.exit(1)


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
