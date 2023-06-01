import os
import shutil
import subprocess
import sys
import tempfile

from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table
import click
from .base import find_all_photons, find_photon, remove_photon
from . import api
import lepton.remote as remote
from lepton.photon.constants import METADATA_VCS_URL_KEY
from lepton.photon.download import fetch_code_from_vcs

console = Console(highlight=False)


def get_remote_url(ctx, param, value):
    value = remote.get_remote_url(value)
    if value is not None:
        console.print(f"Using remote cluster: [green]{value}[/green]")
    else:
        console.print("Using [green]local server[/green]")
    return value


@click.group()
def photon():
    pass


@photon.command()
@click.option("--name", "-n", help="Name of the Photon", required=True)
@click.option("--model", "-m", help="Model spec", required=True)
def create(name, model):
    console.print(f"Creating Photon: [green]{name}[/green]")
    try:
        photon = api.create(name=name, model=model)
    except Exception as e:
        console.print(f"Failed to create Photon:\n{e}")
        sys.exit(1)
    try:
        api.save(photon)
    except Exception as e:
        console.print(f'Failed to save Photon: "{e}"')
        sys.exit(1)
    console.print(f"Photon [green]{name}[/green] created")


@photon.command()
@click.option(
    "--name",
    "-n",
    help="Name of the Photon (The lastest version of the Photon will be used)",
)
@click.option("--id", "-i", "id_", help="ID of the Photon")
@click.option(
    "--remote_url",
    "-r",
    help="Remote URL of the Lepton Server",
)
def remove(name, id_, remote_url):
    remote_url = remote.get_remote_url(remote_url)

    if remote_url is not None and id_ is None:
        # TODO: Support remove remote by name
        console.print("Must specify --id when removing remote photon")
        sys.exit(1)
    if remote_url is None and name is None:
        console.print("Must specify --name when removing local photon")
        sys.exit(1)

    if remote_url is not None:
        if api.remove_remote(remote_url, id_):
            console.print(f'Remote photon "{id_}" [green]removed[/]')
        else:
            console.print(f'Remote photon "{id_}" [red]does not exist[/]')
        return

    if find_photon(name) is None:
        console.print(f'Photon "{name}" [red]does not exist[/]')
        sys.exit(1)
    remove_photon(name)
    console.print(f'Photon "{name}" [green]removed[/]')


@photon.command()
@click.option(
    "--remote_url",
    "-r",
    help="Remote URL of the Lepton Server",
    callback=get_remote_url,
)
def list(remote_url):
    if remote_url is not None:
        # TODO: Add Creation Time and other metadata
        photons = api.list_remote(remote_url)
        records = [
            (photon["name"], photon["model"], photon["id"]) for photon in photons
        ]
    else:
        records = find_all_photons()
        records = [
            (name, model, id_) for id_, name, model, path, creation_time in records
        ]

    table = Table(title="Photons", show_lines=True)
    table.add_column("Name")
    table.add_column("Model")
    table.add_column("ID")

    records_by_name = {}
    for name, model, id_ in records:
        records_by_name.setdefault(name, []).append((model, id_))
    for name, sub_records in records_by_name.items():
        model_table = Table(show_header=False, box=None)
        id_table = Table(show_header=False, box=None)
        for model, id_ in sub_records:
            model_table.add_row(model)
            id_table.add_row(id_)
        table.add_row(name, model_table, id_table)
    console.print(table)


@photon.command()
@click.option("--name", "-n", help="Name of the Photon")
@click.option("--model", "-m", help="Model Spec")
@click.option("--file", "-f", "path", help="Path to .photon file")
@click.option("--port", "-p", help="Port to run on", default=8080)
@click.option(
    "--remote_url",
    "-r",
    help="Remote URL of the Lepton Server",
)
@click.option("--id", "-i", help="ID of the Photon")
@click.pass_context
def run(ctx, name, model, path, port, remote_url, id):
    remote_url = remote.get_remote_url(remote_url)

    if remote_url is not None:
        if id is None:
            # TODO: Support run remote by name
            # TODO: Support push and run if the Photon does not exist on remote
            console.print("Must specify --id when running remote photon")
            sys.exit(1)
        api.remote_launch(id, remote_url)
        return

    if name is None and path is None:
        console.print("Must specify either --name or --path")
        sys.exit(1)
    if path is None:
        path = find_photon(name)
    if path is None or not os.path.exists(path):
        name_or_path = name if name is not None else path
        console.print(f'Photon "{name_or_path}" [red]does not exist[/]')
        if name and model:
            ctx.invoke(create, name=name, model=model)
            path = find_photon(name)
        else:
            sys.exit(1)

    metadata = api.load_metadata(path)

    if metadata.get(METADATA_VCS_URL_KEY, None):
        workpath = fetch_code_from_vcs(metadata[METADATA_VCS_URL_KEY])
        os.chdir(workpath)
    photon = api.load(path)
    photon.launch(port=port)


# Only used by platform to prepare the environment inside the container and not
# meant to be used by users
@photon.command(hidden=True)
@click.option("--file", "-f", "path", help="Path to .photon file")
@click.pass_context
def prepare(ctx, path):
    metadata = api.load_metadata(path)

    default_requirement_dependency = []
    if metadata.get(METADATA_VCS_URL_KEY, None):
        workpath = fetch_code_from_vcs(metadata[METADATA_VCS_URL_KEY])
        if os.path.exists(os.path.join(workpath, "requirements.txt")):
            with open(os.path.join(workpath, "requirements.txt")) as f:
                default_requirement_dependency = f.read().splitlines()

    # pip install
    requirement_dependency = metadata.get(
        "requirement_dependency", default_requirement_dependency
    )
    if requirement_dependency:
        with tempfile.NamedTemporaryFile("w") as f:
            content = "\n".join(requirement_dependency)
            f.write(content)
            f.flush()
            console.print(f"Installing requirement_dependency:\n{content}")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "-r", f.name]
                )
            except subprocess.CalledProcessError as e:
                console.print(f"Failed to install {e}")
                sys.exit(1)

    # TODO: Support yum install
    # apt/apt-get install
    system_dependency = metadata.get("system_dependency", [])
    if system_dependency:
        apt = shutil.which("apt") or shutil.which("apt-get")
        if not apt:
            console.print(
                "Cannot install system dependency because apt/apt-get is not available"
            )
            sys.exit(1)
        sudo = shutil.which("sudo")
        if not sudo:
            console.print(
                "Cannot install system dependency because sudo is not available"
            )
            sys.exit(1)

        if Confirm.ask(
            f"Installing system dependency will run with sudo ({sudo}), continue?",
            default=True,
        ):
            console.print(f"Installing system_dependency:\n{system_dependency}")
            try:
                subprocess.check_call([sudo, apt, "update"])
                subprocess.check_call([sudo, apt, "install", "-y"] + system_dependency)
            except subprocess.CalledProcessError as e:
                console.print(f"Failed to {apt} install: {e}")
                sys.exit(1)


@photon.command()
@click.option("--name", "-n", help="Name of the Photon", required=True)
@click.option(
    "--remote_url",
    "-r",
    help="Remote URL of the Lepton Server",
    callback=get_remote_url,
)
def push(name, remote_url):
    path = find_photon(name)
    if path is None or not os.path.exists(path):
        console.print(f'Photon "{name}" [red]does not exist[/]')
        sys.exit(1)
    api.push(path, remote_url)
    console.print(f'Photon "{name}" [green]pushed[/]')


@photon.command()
@click.option("--id", "-i", help="ID of the Photon", required=True)
@click.option(
    "--remote_url",
    "-r",
    help="Remote URL of the Lepton Server",
    callback=get_remote_url,
)
@click.option("--file", "-f", "path", help="Path to .photon file")
def fetch(id, remote_url, path):
    photon = api.fetch(id, remote_url, path)
    console.print(f'Photon "{photon.name}:{id}" [green]fetched[/]')


def add_command(click_group):
    click_group.add_command(photon)
