from datetime import datetime
import os
import re
import shutil
import subprocess
import socket
import sys
import tempfile

from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table
import click
from leptonai.photon.base import (
    find_all_local_photons,
    find_local_photon,
    remove_local_photon,
)
from leptonai.api import photon as api
from leptonai.api import workspace
from .util import click_group
from leptonai.photon.constants import METADATA_VCS_URL_KEY
from leptonai.photon.download import fetch_code_from_vcs
from leptonai.api.deployment import list_deployment
from leptonai.api.storage import check_path_exists

console = Console(highlight=False)


def _get_ordered_photon_ids_or_none(workspace_url, auth_token, name):
    """Returns a list of photon ids for a given name, in the order newest to
    oldest. If no photon of such name exists, returns None.
    """
    photons = api.list_remote(workspace_url, auth_token)
    target_photons = [p for p in photons if p["name"] == name]
    if len(target_photons) == 0:
        return None
    target_photons.sort(key=lambda p: p["created_at"], reverse=True)
    return [p["id"] for p in target_photons]


def get_most_recent_photon_id_or_none(workspace_url, auth_token, name):
    """Returns the most recent photon id for a given name. If no photon of such
    name exists, returns None.
    """
    photon_ids = _get_ordered_photon_ids_or_none(workspace_url, auth_token, name)
    return photon_ids[0] if photon_ids else None


def is_port_occupied(port):
    """
    Returns True if the port is occupied, False otherwise.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


@click_group()
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
    help=(
        "Name of the Photon to delete. If --all is specified, all versions of the"
        " Photon with this name will be deleted. Otherwise, remove the latest"
        " version of the Photon with this name."
    ),
)
@click.option("--local", "-l", is_flag=True, help="Remove local photon.")
@click.option("--id", "-i", "id_", help="ID of the Photon")
@click.option(
    "--all", "-a", "all_", is_flag=True, help="Remove all versions of the Photon"
)
def remove(name, local, id_, all_):
    workspace_url = workspace.get_workspace_url()

    if name and id_:
        console.print("Cannot specify both --name and --id. Use one or the other.")
        sys.exit(1)
    if name is None and id_ is None:
        console.print("Must specify either --name or --id.")
        sys.exit(1)

    if not local and workspace_url is not None:
        # Remove remote photon.
        auth_token = workspace.get_auth_token(workspace_url)
        # Find ids that we need to remove
        if name:
            # Remove all versions of the photon.
            ids = _get_ordered_photon_ids_or_none(workspace_url, auth_token, name)
            ids = [ids[0]] if not all_ else ids
        else:
            ids = [id_]
        # Check if things actually exist.
        if len(ids) == 0:
            if name:
                console.print(f"Cannot find photon with name [red]{name}[/].")
            else:
                console.print(f"Cannot find photon with id [red]{id_}[/].")
            sys.exit(1)
        # Actually remove the ids
        for id_to_remove in ids:
            if api.remove_remote(workspace_url, id_to_remove, auth_token):
                console.print(f"Photon id [green]{id_to_remove}[/] removed.")
            else:
                console.print(f"Error when removing photon id [red]{id_to_remove}[/].")
                console.print(
                    "There may be a network error or race condition. You may"
                    " want to try again."
                )
                sys.exit(1)
        return
    else:
        # local mode
        if name is None:
            # In local mode, photons do not have ids, so we must specify a name.
            console.print("Must specify --name when removing local photon")
            sys.exit(1)
        if find_local_photon(name) is None:
            console.print(f"Photon [red]{name}[/] does not exist.")
            sys.exit(1)
        remove_local_photon(name, remove_all=all_)
        console.print(
            f"{'' if all_ else 'Most recent version of '}Photon [green]{name}[/]"
            " removed."
        )
        return


@photon.command()
@click.option("--local", "-l", help="If specified, list local photons", is_flag=True)
@click.option(
    "--pattern", help="Regular expression pattern to filter Photon names", default=None
)
def list(local, pattern):
    workspace_url = workspace.get_workspace_url()

    if workspace_url is not None and not local:
        console.print(f"Using workspace: [green]{workspace_url}[/green]")
        auth_token = workspace.get_auth_token(workspace_url)
        photons = api.list_remote(workspace_url, auth_token)
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


def _validate_resource_shape(resource_shape: str):
    """
    Utility function to validate the resource shape and exit if invalid.

    :param resource_shape: The resource shape to validate.
    :return: The resource shape if valid.
    """
    # Valid shapes is defined as a list instead of a dict intentionally, because
    # we want to preserve the order of the shapes when printing. Granted, this
    # adds a bit of search time, but the list is small enough that it should not
    # matter.
    # TODO: move the valid shapes and the default valid shape to a common config.
    VALID_SHAPES = ["cpu.small", "cpu.medium", "cpu.large", "gpu.t4", "gpu.a10"]
    DEFAULT_RESOURCE_SHAPE = "cpu.small"
    if not resource_shape:
        # In the default case, we want to use cpu.small.
        return DEFAULT_RESOURCE_SHAPE
    if resource_shape.lower() not in VALID_SHAPES:
        # We will check if the user passed in a valid shape, and if not, we will
        # print a warning.
        # However, we do not want to directly go to an error, because there might
        # be cases when the CLI and the cloud service is out of sync. For example
        # if the user environment has an older version of the CLI while the cloud
        # service has been updated to support more shapes, we want to allow the
        # user to use the new shapes. One can simply ignore the warning and proceed.
        console.print(
            "It seems that you passed in a non-standard resource shape"
            f" [yellow]{resource_shape}[/]. Valid shapes supported by the CLI"
            f" are:\n{VALID_SHAPES}."
        )
    return resource_shape.lower()


@photon.command()
@click.option("--name", "-n", help="Name of the Photon")
@click.option("--model", "-m", help="Model Spec")
@click.option("--file", "-f", "path", help="Path to .photon file")
@click.option(
    "--local",
    "-l",
    help="If specified, run photon on local (can only run locally stored photons)",
    is_flag=True,
)
@click.option("--port", "-p", help="Port to run on", default=8080)
@click.option("--id", "-i", help="ID of the Photon (only required for remote)")
@click.option("--resource-shape", "-r", help="Resource shape required,", default=None)
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
    "--deployment-name",
    "-dn",
    help=(
        "Optional name for the deployment. If not specified, we will attempt to use the"
        " name (if specified) and id as the base name, and find the first non-conflict"
        " name by appending a number."
    ),
    default=None,
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
    local,
    port,
    id,
    resource_shape,
    min_replicas,
    mount,
    deployment_name,
    env,
    secret,
):
    workspace_url = workspace.get_workspace_url()

    if name is not None and id is not None:
        # TODO: support sainity checking that the id matches the name. This
        # will require a remote call to get the names and ids, so for now we
        # will tell users to give either id or name.
        console.print("Must specify either --id or --name, not both.")
        sys.exit(1)

    if not local and workspace_url is not None:
        # remote execution.
        auth_token = workspace.get_auth_token(workspace_url)
        # We first check if id is specified - this is the most specific way to
        # refer to a photon. If not, we will check if name is specified - this
        # might lead to multiple photons, so we will pick the latest one to run
        # as the default behavior.
        # TODO: Support push and run if the Photon does not exist on remote
        if id is None:
            # look for the latest photon with the given name.
            id = get_most_recent_photon_id_or_none(workspace_url, auth_token, name)
            if id is None:
                console.print(f"Photon [red]{name}[/] does not exist.")
                sys.exit(1)
            else:
                console.print(f"Running the most recent version: [green]{id}[/]")
        else:
            console.print(f"Running the specified version: [green]{id}[/]")
        # parse environment variables and secrets
        env_parsed = {}
        secret_parsed = {}
        for s in env:
            try:
                k, v = s.split("=", 1)
            except ValueError:
                console.print(f"Invalid environment definition: [red]{s}[/]")
                sys.exit(1)
            env_parsed[k] = v
        for s in secret:
            # We provide the user a shorcut: instead of having to specify
            # SECRET_NAME=SECRET_NAME, they can just specify SECRET_NAME
            # if the local env name and the secret name are the same.
            k, v = s.split("=", 1) if "=" in s else s, s
            # TODO: sanity check if these secrets exist.
            secret_parsed[k] = v
        mount_parsed = []
        for m in mount:
            try:
                parsed = parse_mount(m)
                if not check_path_exists(workspace_url, parsed["path"]):
                    console.print(f"Path does not exit: [red]{m}[/]")
                    sys.exit(1)

                mount_parsed.append(parsed)
            except ValueError:
                console.print(f"Invalid mount definition: [red]{m}[/]")
                sys.exit(1)
        existing_names = set(
            d["name"] for d in list_deployment(workspace_url, auth_token)
        )
        if deployment_name in existing_names:
            console.print(
                f"Deployment name [red]{deployment_name}[/] already exists. please"
                " choose another one."
            )
            sys.exit(1)
        elif not deployment_name:
            console.print("Attempting to find a proper deployment name.")
            base_name = name if name else id
            # Make sure that deployment name is not longer than 32 characters
            deployment_name = base_name[:32]
            increment = 0
            while deployment_name in existing_names:
                console.print(f"[yellow]{deployment_name}[/] already used.")
                increment += 1
                affix_name = f"-{increment}"
                deployment_name = base_name[: (32 - len(affix_name))] + affix_name
        resource_shape = _validate_resource_shape(resource_shape)
        console.print(f"Launching photon {id} as [green]{deployment_name}[/].")
        api.run_remote(
            id,
            workspace_url,
            resource_shape,
            min_replicas,
            auth_token,
            deployment_name,
            mount_parsed,
            env_parsed,
            secret_parsed,
        )
        return
    else:
        # local execution
        if name is None and path is None:
            console.print("Must specify either --name or --path")
            sys.exit(1)
        if path is None:
            path = find_local_photon(name)

        if path and os.path.exists(path):
            if model:
                metadata = api.load_metadata(path)
                console.print(
                    f"Photon {metadata['name']} was previously created with model"
                    f" {metadata['model']}, newly specify model [yellow]\"{model}\"[/]"
                    " will be ignored"
                )
        else:
            name_or_path = name if name is not None else path
            console.print(f"Photon [red]{name_or_path}[/] does not exist.")
            if name and model:
                ctx.invoke(create, name=name, model=model)
                path = find_local_photon(name)
            else:
                sys.exit(1)

        # envs: parse and set environment variables
        for s in env:
            try:
                k, v = s.split("=", 1)
            except ValueError:
                console.print(f"Invalid environment definition: {s}")
                sys.exit(1)
            os.environ[k] = v
        if mount or secret:
            console.print(
                "Mounts, environment variables and secrets are only supported for"
                " remote execution. They will be ignored for local execution."
            )

        metadata = api.load_metadata(path)

        if metadata.get(METADATA_VCS_URL_KEY, None):
            workpath = fetch_code_from_vcs(metadata[METADATA_VCS_URL_KEY])
            os.chdir(workpath)
        photon = api.load(path)

        # Try to determine if the port is already occupied. If so, we will
        # increment the port number until we find an available one.
        # We try to determine the port as late as possible to minimize the risk
        # of race conditions, although this doesn't completely rule it out.
        #
        # The reason we don't wrap the whole photon.launch() in a try/except
        # block is because we want to catch other exceptions that might be
        # raised by photon.launch() and print them out. Also, photon.launch()
        # might take quite some to init, and we don't want to wait that long
        # before we can tell the user that the port is already occupied. Compared
        # to developer efficiency, we think this is a reasonable tradeoff.
        while is_port_occupied(port):
            console.print(
                f"Port [yellow]{port}[/] already in use. Incrementing port number to"
                " find an available one."
            )
            port += 1
        console.print(f"Launching photon on port: [green]{port}[/]")
        photon.launch(port=port)
        return


# Only used by platform to prepare the environment inside the container and not
# meant to be used by users
@photon.command(hidden=True)
@click.option("--file", "-f", "path", help="Path to .photon file")
@click.pass_context
def prepare(ctx, path):
    metadata = api.load_metadata(path, unpack_extra_files=True)

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
    workspace_url = workspace.get_workspace_url()
    if workspace_url is None:
        console.print("You are not logged in.")
        console.print(
            "You must log in ($lep workspace login) or specify --workspace_url."
        )
        sys.exit(1)
    path = find_local_photon(name)
    if path is None or not os.path.exists(path):
        console.print(f"Photon [red]{name}[/] does not exist.")
        sys.exit(1)

    auth_token = workspace.get_auth_token(workspace_url)
    if not api.push(path, workspace_url, auth_token):
        console.print(f"Photon [red]{name}[/] failed to push.")
        sys.exit(1)
    console.print(f"Photon [green]{name}[/] pushed to workspace.")


@photon.command()
@click.option("--id", "-i", help="ID of the Photon", required=True)
@click.option("--file", "-f", "path", help="Path to .photon file")
def fetch(id, path):
    workspace_url = workspace.get_workspace_url()
    if workspace_url is None:
        console.print("You are not logged in.")
        console.print(
            "To fetch a photon, you must first log in ($lepton workspace login) "
            "to specify a workspace"
        )
    auth_token = workspace.get_auth_token(workspace_url)
    photon = api.fetch(id, workspace_url, path, auth_token)
    console.print(f"Photon [green]{photon.name}:{id}[/] fetched.")


def add_command(cli_group):
    cli_group.add_command(photon)
