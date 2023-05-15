import click
import yaml
import sys

from rich.console import Console
from rich.table import Table

from lepton.config import CACHE_DIR

console = Console(highlight=False)

CLUSTER_FILE = CACHE_DIR / "cluster_info.yaml"


@click.group()
def remote():
    pass


@remote.command()
@click.option("--remote-name", "-n", help="Name of the remote cluster")
@click.option("--remote-url", "-r", help="URL of the remote cluster")
def login(remote_name, remote_url):
    clusters = load_cluster_info()["clusters"]
    if remote_name is not None:
        remote_cluster = clusters.get(remote_name)

        if remote_cluster is None:
            console.print(f'Cluster "{remote_name}" [red]does not exist[/]')
            console.print(
                f'Please use "lepton remote login -r <URL>" to add the remote cluster first'
            )
            sys.exit(1)

        console.print(f"TODO: authenticate")
        set_current_cluster(remote_name)
        console.print(f'Cluster "{remote_name}" [green]logged in[/]')
        return

    if remote_url is not None:
        remote_name = console.input(
            f'Please enter the remote cluster name of "{remote_url}":'
        )
        if len(remote_name) == 0:  # TODO: ask the user to re-enter the name
            console.print(f"Remote cluster name cannot be empty")
            sys.exit(1)

        console.print(f"TODO: authenticate")
        save_cluster(remote_name, remote_url)
        set_current_cluster(remote_name)
        console.print(f'Cluster "{remote_name}" [green]logged in[/]')
        return

    console.print("Must specify --remote-name or --remote-url")
    sys.exit(1)


@remote.command()
def logout():
    set_current_cluster(None)
    console.print(f"[green]Logged out[/]")


@remote.command()
@click.option("--remote-name", "-n", help="Name of the remote cluster", required=True)
def remove(remote_name):
    remove_cluster(remote_name)
    console.print(f'Cluster "{remote_name}" [green]removed[/]')


@remote.command()
def list():
    cluster_info = load_cluster_info()
    clusters = cluster_info["clusters"]
    current_cluster = cluster_info["current_cluster"]
    table = Table()
    table.add_column("Name")
    table.add_column("URL")
    for name, url in clusters.items():
        if name == current_cluster:
            name = f'[green]{name + " (logged in)"}[/]'
            url = f"[green]{url}[/]"
        table.add_row(name, url)
    console.print(table)


def add_command(click_group):
    click_group.add_command(remote)


def load_cluster_info():
    cluster_info = {"clusters": {}, "current_cluster": None}
    if CLUSTER_FILE.exists():
        with open(CLUSTER_FILE) as f:
            cluster_info = yaml.safe_load(f)
    return cluster_info


def save_cluster(name, url):
    cluster_info = load_cluster_info()
    cluster_info["clusters"][name] = url
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


def get_current_cluster_url():
    cluster_info = load_cluster_info()
    current_cluster = cluster_info["current_cluster"]
    if current_cluster is None:
        return None
    clusters = cluster_info["clusters"]
    return clusters[current_cluster]


def get_remote_url(remote_url):
    if remote_url is not None:
        return remote_url
    return get_current_cluster_url()
