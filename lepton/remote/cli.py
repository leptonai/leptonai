import click
import yaml
import sys

from rich.console import Console
from rich.table import Table

from lepton.config import CACHE_DIR
from .util import is_command_installed, generate_random_string, run_terraform_apply, run_terraform_destroy


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
                'Please use "lepton remote login -r <URL>" to add the remote cluster first'
            )
            sys.exit(1)

        set_current_cluster(remote_name)
        console.print(f'Cluster "{remote_name}" [green]logged in[/]')
        return

    if remote_url is not None:
        remote_name = None
        while not remote_name:
            remote_name = console.input(
                f'Please enter the remote cluster name for "{remote_url}": '
            )
            if not remote_name:
                console.print("Remote cluster name cannot be empty")
        
        auth_token = console.input(
            f'Please enter the authentication token for "{remote_name}" (ENTER if none): '
        ) or None
        
        save_cluster(remote_name, remote_url, auth_token = auth_token)
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
@click.option("--remote-name", "-n", help="Name of the remote cluster", required=True)
def remove(remote_name):
    cluster_info = load_cluster_info()["clusters"].get(remote_name)
    if cluster_info is None:
        console.print(f'Cluster "{remote_name}" [red]does not exist[/]')
        sys.exit(1)

    dir = cluster_info.get("terraform_dir")
    if dir is not None:
        if not run_terraform_destroy(dir, remote_name):
            console.print(f"Failed to destroy cluster {remote_name} with terraform")
            sys.exit(1)

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
@click.option("--remote-name", "-n", help="Name of the remote cluster", default=None)
@click.option("--sandbox", "-s", help="Sandbox name", is_flag=True, default=True)
@click.option("--provider", "-p", help="Provider name", default="aws")
def create(remote_name, sandbox, provider):
    if remote_name is None:
        remote_name = "lepton-cluster-" + generate_random_string(5)
        # TODO: check if the name already exists
    if sandbox is False:
        console.print("TODO: support a non-sandbox cluster")
        sys.exit(1)
    if provider != "aws":
        console.print("TODO: support non-aws providers")
        sys.exit(1)

    if not meet_create_precondition():
        console.print("Installation precondition not met. Please check the error message above.")
        sys.exit(1)

    console.print(f"Creating cluster {remote_name} on AWS")

    # TODO: pass in cluster name
    # TODO: pass in auth token
    dir = CACHE_DIR / "cluster_states" / remote_name
    success, ingress_hostname = run_terraform_apply(dir, remote_name)
    if not success:
        console.print(f"Failed to create cluster {remote_name} with terraform")
        sys.exit(1)

    save_cluster(remote_name, f"http://{ingress_hostname}", terraform_dir = str(dir))
    console.print(f"Cluster {remote_name} created successfully")
    console.print(f"The ingress URL is http://{ingress_hostname}")

    console.print(f"Run `lepton remote login -n {remote_name}` to login to the created cluster")


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


def get_current_cluster_url():
    cluster_info = load_cluster_info()
    current_cluster = cluster_info["current_cluster"]
    if current_cluster is None:
        return None
    clusters = cluster_info["clusters"]
    return clusters[current_cluster]["url"]


def get_remote_url(remote_url):
    if remote_url is not None:
        return remote_url
    return get_current_cluster_url()


def meet_create_precondition():
    if not is_command_installed("terraform"):
        console.print("Terraform is not installed. Please install Terraform first.")
        return False
    if not is_command_installed("aws"):
        console.print("AWS is not installed. Please install AWS first.")
        return False
    if not is_command_installed("git"):
        console.print("Git is not installed. Please install Git first.")
        return False
    # TODO: check if the user has AWS credentials
    return True
