from datetime import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile

from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table
import click
from .base import find_all_local_photons, find_photon, remove_photon
from . import api
import leptonai.remote as remote
from leptonai.photon.constants import METADATA_VCS_URL_KEY
from leptonai.photon.download import fetch_code_from_vcs

console = Console(highlight=False)


def get_remote_url(ctx, param, value):
    value = remote.get_remote_url(value)
    if value is not None:
        console.print(f"Using remote cluster: [green]{value}[/green]")
    else:
        console.print("Using [green]local server[/green]")
    return value


def get_most_recent_photon_id_or_none(remote_url, auth_token, name):
    """
    Returns the most recent photon id for a given name. If no photon of such
    name exists, returns None.
    """
    photons = api.list_remote(remote_url, auth_token)
    target_photons = [p for p in photons if p["name"] == name]
    if len(target_photons) == 0:
        return None
    photon_id = max(target_photons, key=lambda p: p["created_at"])["id"]
    return photon_id


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
    help="Name of the Photon (The latest version of the Photon will be removed)",
)
@click.option("--id", "-i", "id_", help="ID of the Photon")
def remove(name, id_):
    remote_url = remote.get_remote_url()

    if remote_url is not None:
        auth_token = remote.cli.get_auth_token(remote_url)
        if id_ is None and name is None:
            console.print("Must specify --id or --name when removing remote photon.")
            sys.exit(1)
        elif id_ is None:
            # Default behavior without id is to remove the most recent photon.
            id_ = get_most_recent_photon_id_or_none(remote_url, auth_token, name)
            if id_ is None:
                console.print(f'Photon "{name}" [red]does not exist[/]')
                sys.exit(1)

            if (
                console.input(
                    f'remove photon "[green]{name}[/]" with id '
                    f'"[green]{id_}[/]"?[y/n]: '
                )
                != "y"
            ):
                sys.exit(0)

        if api.remove_remote(remote_url, id_, auth_token):
            console.print(f'Remote photon "{id_}" [green]removed[/]')
        else:
            # TODO: if we do find the photon, but it's not removed, should we
            # assume that it does not exist (because it did exist), or should
            # we do something else?
            console.print(f'Remote photon "{id_}" [red]does not exist[/]')
        return
    elif name is None:
        # In local mode, photons do not have ids, so we must specify a name.
        console.print("Must specify --name when removing local photon")
        sys.exit(1)
    elif find_photon(name) is None:
        console.print(f'Photon "{name}" [red]does not exist[/]')
        sys.exit(1)
    remove_photon(name)
    console.print(f'Photon "{name}" [green]removed[/]')


@photon.command()
@click.option("--local", "-l", help="If specified, list local photons", is_flag=True)
@click.option(
    "--pattern", help="Regular expression pattern to filter Photon names", default=None
)
def list(local, pattern):
    remote_url = remote.get_remote_url()

    if remote_url is not None and not local:
        console.print(f"Using remote cluster: [green]{remote_url}[/green]")
        auth_token = remote.cli.get_auth_token(remote_url)
        photons = api.list_remote(remote_url, auth_token)
        # Note: created_at returned by the server is in milliseconds, and as a
        # result we need to divide by 1000 to get seconds that is understandable
        # by the Python CLI.
        records = [
            (photon["name"], photon["model"], photon["id"], photon["created_at"] / 1000)
            for photon in photons
        ]
    else:
        records = find_all_local_photons()
        records = [
            (name, model, id_, creation_time)
            for id_, name, model, path, creation_time in records
        ]

    table = Table(title="Photons", show_lines=True)
    table.add_column("Name")
    table.add_column("Model")
    table.add_column("ID")
    table.add_column("Created At")

    records_by_name = {}
    for name, model, id_, creation_time in records:
        if pattern is None or re.match(pattern, name):
            records_by_name.setdefault(name, []).append((model, id_, creation_time))

    # Sort by creation time and print
    for name, sub_records in records_by_name.items():
        sub_records.sort(key=lambda r: r[2], reverse=True)
        model_table = Table(show_header=False, box=None)
        id_table = Table(show_header=False, box=None)
        creation_table = Table(show_header=False, box=None)
        for model, id_, creation_time in sub_records:
            model_table.add_row(model)
            id_table.add_row(id_)
            # Photon database stores creation time as a timestamp in
            # milliseconds, so we need to convert.
            creation_table.add_row(
                datetime.fromtimestamp(creation_time).strftime("%Y-%m-%d %H:%M:%S")
            )
        table.add_row(name, model_table, id_table, creation_table)
    console.print(table)


def parse_mount(mount_str: str):
    parts = mount_str.split(":")
    if len(parts) == 2:
        return {"path": parts[0].strip(), "mount_path": parts[1].strip()}
    else:
        raise ValueError(f"Invalid mount: {mount_str}")


@photon.command()
@click.option("--name", "-n", help="Name of the Photon")
@click.option("--model", "-m", help="Model Spec")
@click.option("--file", "-f", "path", help="Path to .photon file")
@click.option("--port", "-p", help="Port to run on", default=8080)
@click.option("--id", "-i", help="ID of the Photon (only required for remote)")
@click.option("--cpu", help="Number of CPU to require", default=1)
@click.option("--memory", help="Number of RAM to require in MB", default=1024)
@click.option("--min-replicas", help="Number of replicas", default=1)
@click.option(
    "--mount",
    help=(
        "Storage to be mounted to the deployment, in the format"
        " STORAGE_PATH:MOUNT_PATH."
    ),
    multiple=True,
)
@click.option(
    "--deployment-name", "-dn", help="Optional name for the deployment", default=None
)
@click.option(
    "--env",
    "-e",
    help="Environment variables to pass to the deployment, in the format NAME=VALUE.",
    multiple=True,
)
@click.option(
    "--secret",
    "-s",
    help=(
        "Secrets to pass to the deployment, in the format NAME=SECRET_NAME. If"
        " SECRET_NAME is also going to be the name of the environment variable, you can"
        " omit it and simply pass SECRET_NAME."
    ),
    multiple=True,
)
@click.pass_context
def run(
    ctx,
    name,
    model,
    path,
    port,
    id,
    cpu,
    memory,
    min_replicas,
    mount,
    deployment_name,
    env,
    secret,
):
    remote_url = remote.get_remote_url()

    if name is not None and id is not None:
        # TODO: support sainity checking that the id matches the name. This
        # will require a remote call to get the names and ids, so for now we
        # will tell users to give either id or name.
        console.print("Must specify either --id or --name, not both.")
        sys.exit(1)

    if remote_url is not None:
        auth_token = remote.cli.get_auth_token(remote_url)
        # We first check if id is specified - this is the most specific way to
        # refer to a photon. If not, we will check if name is specified - this
        # might lead to multiple photons, so we will pick the latest one to run
        # as the default behavior.
        # TODO: Support push and run if the Photon does not exist on remote
        if id is None:
            # look for the latest photon with the given name.
            id = get_most_recent_photon_id_or_none(remote_url, auth_token, name)
            if id is None:
                console.print(f'Photon "{name}" [red]does not exist[/]')
                sys.exit(1)
            else:
                console.print(f"Running the most recent version: [green]{id}[/]")
        else:
            console.print("Running the specified version: [green]{id}[/]")
        # parse environment variables and secrets
        env_parsed = {}
        secret_parsed = {}
        for s in env:
            try:
                name, value = s.split("=", 1)
            except ValueError:
                console.print(f"Invalid environment definition: {s}")
                sys.exit(1)
            env_parsed[name] = value
        for s in secret:
            # We provide the user a shorcut: instead of having to specify
            # SECRET_NAME=SECRET_NAME, they can just specify SECRET_NAME
            # if the local env name and the secret name are the same.
            name, secret_name = s.split("=", 1) if name in s else s, s
            # TODO: sanity check if these secrets exist.
            secret_parsed[name] = secret_name
        mount_parsed = []
        for m in mount:
            try:
                mount_parsed.append(parse_mount(m))
            except ValueError:
                console.print(f"Invalid mount definition: {m}")
                sys.exit(1)
        api.remote_launch(
            id,
            remote_url,
            cpu,
            memory,
            min_replicas,
            auth_token,
            mount_parsed,
            deployment_name,
            env_parsed,
            secret_parsed,
        )
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

    if metadata.get(METADATA_VCS_URL_KEY, None):
        fetch_code_from_vcs(metadata[METADATA_VCS_URL_KEY])

    # pip install
    requirement_dependency = metadata.get("requirement_dependency", [])
    if requirement_dependency:
        with tempfile.NamedTemporaryFile("w", suffix=".txt") as f:
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

        confirmed = (not sys.stdin.isatty()) or Confirm.ask(
            f"Installing system dependency will run with sudo ({sudo}), continue?",
            default=True,
        )
        if confirmed:
            console.print(f"Installing system_dependency:\n{system_dependency}")
            try:
                subprocess.check_call([sudo, apt, "update"])
                subprocess.check_call([sudo, apt, "install", "-y"] + system_dependency)
            except subprocess.CalledProcessError as e:
                console.print(f"Failed to {apt} install: {e}")
                sys.exit(1)


@photon.command()
@click.option("--name", "-n", help="Name of the Photon", required=True)
def push(name):
    remote_url = remote.get_remote_url()
    if remote_url is None:
        console.print("You are not logged in.")
        console.print("You must log in ($lep remote login) or specify --remote_url.")
        sys.exit(1)
    path = find_photon(name)
    if path is None or not os.path.exists(path):
        console.print(f'Photon "{name}" [red]does not exist[/]')
        sys.exit(1)

    auth_token = remote.cli.get_auth_token(remote_url)
    if not api.push(path, remote_url, auth_token):
        console.print(f'Photon "{name}" [red]failed to push[/]')
        sys.exit(1)
    console.print(f'Photon "{name}" [green]pushed[/]')


@photon.command()
@click.option("--id", "-i", help="ID of the Photon", required=True)
@click.option("--file", "-f", "path", help="Path to .photon file")
def fetch(id, path):
    remote_url = remote.get_remote_url()
    if remote_url is None:
        console.print("You are not logged in.")
        console.print(
            "To fetch a photon, you must first log in ($lepton remote login) "
            "to specify a remote cluster"
        )
    auth_token = remote.cli.get_auth_token(remote_url)
    photon = api.fetch(id, remote_url, path, auth_token)
    console.print(f'Photon "{photon.name}:{id}" [green]fetched[/]')


def add_command(click_group):
    click_group.add_command(photon)
