from datetime import datetime
import os
import re
import shutil
import subprocess
import socket
import sys
import tempfile
from typing import Optional
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
from .util import (
    click_group,
    guard_api,
    check,
    get_workspace_and_token_or_die,
    explain_response,
    APIError,
)
from leptonai.photon.constants import METADATA_VCS_URL_KEY
from leptonai.photon.download import fetch_code_from_vcs
from leptonai.api.deployment import list_deployment
from leptonai.api.storage import check_path_exists
from leptonai.config import LEPTON_RESERVED_ENV_PREFIX

console = Console(highlight=False)


def _get_ordered_photon_ids_or_none(workspace_url, auth_token, name):
    """Returns a list of photon ids for a given name, in the order newest to
    oldest. If no photon of such name exists, returns None.
    """
    photons = api.list_remote(workspace_url, auth_token)
    guard_api(
        photons, msg=f"Failed to list photons in workspace [red]{workspace_url}[/]."
    )
    target_photons = [p for p in photons if p["name"] == name]
    if len(target_photons) == 0:
        return None
    target_photons.sort(key=lambda p: p["created_at"], reverse=True)
    return [p["id"] for p in target_photons]


def _get_most_recent_photon_id_or_none(
    workspace_url, auth_token, name
) -> Optional[str]:
    """Returns the most recent photon id for a given name. If no photon of such
    name exists, returns None.
    """
    photon_ids = _get_ordered_photon_ids_or_none(workspace_url, auth_token, name)
    return photon_ids[0] if photon_ids else None


def _find_available_port(port):
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
    def is_port_occupied(port):
        """
        Returns True if the port is occupied, False otherwise.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", port)) == 0

    while is_port_occupied(port):
        console.print(
            f"Port [yellow]{port}[/] already in use. Incrementing port number to"
            " find an available one."
        )
        port += 1
    return port


@click_group()
def photon():
    """
    Manages photons locally and on the Lepton AI cloud.

    Photon is at the core of Lepton AI's abstraction: it is a Python centric
    abstraction of an AI model or application, and provides a simple interface
    to specify dependencies, extra files, and environment variables. For more
    details, see `leptonai.photon.Photon`.

    The photon command is used to create photons locally, push and fetch photons
    between local and remote, and run, list and delete photons either locally or
    remotely.
    """
    pass


@photon.command()
@click.option("--name", "-n", help="Name of the photon", required=True)
@click.option("--model", "-m", help="Model spec", required=True)
def create(name, model):
    """
    Creates a new photon in the local environment.
    For specifics on the model spec, see `leptonai.photon.Photon`. To push a photon
    to the workspace, use `lep photon push`.

    Developer note: insert a link to the photon documentation here.
    """
    try:
        photon = api.create(name=name, model=model)
    except Exception as e:
        console.print(f"Failed to create photon: [red]{e}[/]")
        sys.exit(1)
    try:
        api.save(photon)
    except Exception as e:
        console.print(f"Failed to save photon: [red]{e}[/]")
        sys.exit(1)
    console.print(f"Photon [green]{name}[/green] created.")


@photon.command()
@click.option(
    "--name",
    "-n",
    help=(
        "Name of the photon to delete. If `--all` is specified, all versions of the"
        " photon with this name will be deleted. Otherwise, remove the latest"
        " version of the photon with this name."
    ),
)
@click.option(
    "--local", "-l", is_flag=True, help="Remove local photons instead of remote."
)
@click.option(
    "--id", "-i", "id_", help="The specific version id of the photon to remove."
)
@click.option(
    "--all", "-a", "all_", is_flag=True, help="Remove all versions of the photon."
)
def remove(name, local, id_, all_):
    """
    Removes a photon. The behavior of this command depends on whether one has
    logged in to the Lepton AI cloud via `lep login`. If one has logged in, this
    command will remove the photon from the workspace. Otherwise, or of `--local`
    is explicitly specified, it will remove the photon from the local environment.
    """
    workspace_url = workspace.get_current_workspace_url()

    check(
        not (name and id_), "Cannot specify both --name and --id. Use one or the other."
    )
    check(name or id_, "Must specify either --name or --id.")

    if not local and workspace_url is not None:
        # Remove remote photon.
        auth_token = workspace.get_auth_token(workspace_url)
        # Find ids that we need to remove
        if name:
            # Remove all versions of the photon.
            ids = _get_ordered_photon_ids_or_none(workspace_url, auth_token, name)
            check(ids, f"Cannot find photon with name [yellow]{name}[/].")
            ids = [ids[0]] if (not all_) else ids
        else:
            ids = [id_]
        # Actually remove the ids
        for id_to_remove in ids:
            explain_response(
                api.remove_remote(workspace_url, auth_token, id_to_remove),
                f"Photon id [green]{id_to_remove}[/] removed.",
                f"Photon id [red]{id_to_remove}[/] not removed. See error message"
                " above.",
                f"Photon id [red]{id_to_remove}[/] not removed. See error message"
                " above.",
                exit_if_4xx=True,
            )
        return
    else:
        # local mode
        check(name, "Must specify --name when removing local photon")
        check(find_local_photon(name), f"Photon [red]{name}[/] does not exist.")
        remove_local_photon(name, remove_all=all_)
        console.print(
            f"{'' if all_ else 'Latest version of '}Photon [green]{name}[/] removed."
        )
        return


@photon.command()
@click.option("--local", "-l", help="If specified, list local photons", is_flag=True)
@click.option(
    "--pattern", help="Regular expression pattern to filter photon names", default=None
)
def list(local, pattern):
    """
    Lists all photons. If one has logged in to the Lepton AI cloud via `lep login`,
    this command will list all photons in the Lepton AI cloud. Otherwise, or if
    `--local` is explicitly specified, it will list all photons in the local
    environment.
    """
    workspace_url = workspace.get_current_workspace_url()

    if workspace_url is not None and not local:
        auth_token = workspace.get_auth_token(workspace_url)
        photons = guard_api(
            api.list_remote(workspace_url, auth_token),
            detail=True,
            msg=f"Failed to list photons in workspace [red]{workspace_url}[/].",
        )
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
            for id_, name, model, _, creation_time in records
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
            # photon database stores creation time as a timestamp in
            # milliseconds, so we need to convert.
            creation_table.add_row(
                datetime.fromtimestamp(creation_time).strftime("%Y-%m-%d %H:%M:%S")
            )
        table.add_row(name, model_table, id_table, creation_table)
    console.print(table)


def _parse_mount_or_die(url: str, auth: Optional[str], mount: str):
    """
    Utility function to parse a mount string into a dict.
    """
    mount_parsed = []
    for mount_str in mount:
        parts = mount_str.split(":")
        if len(parts) == 2:
            mount_parsed.append(
                {"path": parts[0].strip(), "mount_path": parts[1].strip()}
            )
            check(
                check_path_exists(url, auth, parts[0].strip()),
                f"Path [red]{parts[0].strip()}[/] does not exist.",
            )
        else:
            console.print(f"Invalid mount definition: [red]{mount_str}[/]")
            sys.exit(1)
    return mount_parsed


# Valid shapes is defined as a list instead of a dict intentionally, because
# we want to preserve the order of the shapes when printing. Granted, this
# adds a bit of search time, but the list is small enough that it should not
# matter.
# TODO: move the valid shapes and the default valid shape to a common config.
VALID_SHAPES = ["cpu.small", "cpu.medium", "cpu.large", "gpu.t4", "gpu.a10"]
DEFAULT_RESOURCE_SHAPE = "cpu.small"


def _get_valid_shapes():
    """
    Utility function to get the valid shapes as a string.
    """
    if len(VALID_SHAPES) > 7:
        return ", ".join(VALID_SHAPES[:7]) + ", ..."
    return ", ".join(VALID_SHAPES)


def _validate_resource_shape(resource_shape: str):
    """
    Utility function to validate the resource shape and exit if invalid.

    :param resource_shape: The resource shape to validate.
    :return: The resource shape if valid.
    """
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
            f" [yellow]{resource_shape}[/]."
        )
        console.print(f"Valid shapes supported by the CLI are:\n{VALID_SHAPES}.")
    return resource_shape.lower()


def _parse_env_and_secret_or_die(env, secret):
    env_parsed = {}
    secret_parsed = {}
    for s in env:
        try:
            k, v = s.split("=", 1)
        except ValueError:
            console.print(f"Invalid environment definition: [red]{s}[/]")
            sys.exit(1)
        check(
            not k.lower().startswith(LEPTON_RESERVED_ENV_PREFIX),
            "Environment variable name cannot start with reserved prefix"
            f" {LEPTON_RESERVED_ENV_PREFIX}. Found {k}.",
        )
        env_parsed[k] = v
    for s in secret:
        # We provide the user a shorcut: instead of having to specify
        # SECRET_NAME=SECRET_NAME, they can just specify SECRET_NAME
        # if the local env name and the secret name are the same.
        k, v = s.split("=", 1) if "=" in s else (s, s)
        check(
            not k.lower().startswith(LEPTON_RESERVED_ENV_PREFIX),
            "Secret name cannot start with reserved prefix"
            f" {LEPTON_RESERVED_ENV_PREFIX}. Found {k}.",
        )
        # TODO: sanity check if these secrets exist.
        secret_parsed[k] = v
    return env_parsed, secret_parsed


def _find_deployment_name_or_die(workspace_url, auth_token, name, id, deployment_name):
    deployments = guard_api(
        list_deployment(workspace_url, auth_token),
        detail=True,
        msg="Failed to list deployments.",
    )
    existing_names = set(d["name"] for d in deployments)
    check(
        deployment_name not in existing_names,
        f"Deployment [red]{deployment_name}[/] already exists. please"
        " choose another name.",
    )
    if not deployment_name:
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
    return deployment_name


def _parse_deployment_tokens_or_die(public, tokens):
    """
    Utility function to parse deployment tokens.
    """
    check(
        not (public and tokens),
        "If you specify a deployment to be public, it cannot have deployment"
        " tokens at the same time.",
    )
    if public:
        return []
    else:
        # We will always include the workspace token as acceptable tokens
        # for the deployment.
        final_tokens = [{"value_from": {"token_name_ref": "WORKSPACE_TOKEN"}}]
        if tokens:
            final_tokens.extend([{"value": token} for token in tokens])
        return final_tokens


@photon.command()
@click.option("--name", "-n", help="Name of the photon to run.")
@click.option("--model", "-m", help="Model spec of the photon.")
@click.option(
    "--file", "-f", "path", help="Path to the specific `.photon` file to run."
)
@click.option(
    "--local",
    "-l",
    help=(
        "If specified, run photon locally (note that this can only run locally stored"
        " photons)"
    ),
    is_flag=True,
)
@click.option("--port", "-p", help="Port to run on.", default=8080)
@click.option("--id", "-i", help="ID of the photon (only required for remote).")
@click.option(
    "--resource-shape",
    help="Resource shape (valid values are: " + _get_valid_shapes() + ").",
    default=None,
)
@click.option("--min-replicas", help="Number of replicas.", default=1)
@click.option(
    "--mount",
    help=(
        "Persistent storage to be mounted to the deployment, in the format"
        " `STORAGE_PATH:MOUNT_PATH`."
    ),
    multiple=True,
)
@click.option(
    "--deployment-name",
    "-dn",
    help=(
        "Optional name for the deployment. If not specified, we will attempt to use the"
        " name (if specified) or id as the base name, and find the first non-conflict"
        " name by appending a number."
    ),
    default=None,
)
@click.option(
    "--env",
    "-e",
    help="Environment variables to pass to the deployment, in the format `NAME=VALUE`.",
    multiple=True,
)
@click.option(
    "--secret",
    "-s",
    help=(
        "Secrets to pass to the deployment, in the format `NAME=SECRET_NAME`. If"
        " secret name is also the environment variable name, you can"
        " omit it and simply pass `SECRET_NAME`."
    ),
    multiple=True,
)
@click.option(
    "--public",
    is_flag=True,
    help=(
        "If specified, the photon will be publicly accessible. See docs for details "
        "on access control."
    ),
)
@click.option(
    "--tokens",
    help=(
        "Additional tokens that can be used to access the photon. See docs for details "
        "on access control."
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
    public,
    tokens,
):
    """
    Runs a photon. If one has logged in to the Lepton AI cloud via `lep login`,
    the photon will be run on the cloud. Otherwise, or if `--local` is specified,
    the photon will be run locally.

    Refer to the documentation for a more detailed description on the choices
    among `--name`, `--model`, `--path` and `--id`.
    """
    workspace_url = workspace.get_current_workspace_url()

    check(not (name and id), "Must specify either --id or --name, not both.")

    if not local and workspace_url is not None:
        # remote execution.
        auth_token = workspace.get_auth_token(workspace_url)
        # We first check if id is specified - this is the most specific way to
        # refer to a photon. If not, we will check if name is specified - this
        # might lead to multiple photons, so we will pick the latest one to run
        # as the default behavior.
        # TODO: Support push and run if the photon does not exist on remote
        if id is None:
            # look for the latest photon with the given name.
            id = _get_most_recent_photon_id_or_none(workspace_url, auth_token, name)
            check(
                id,
                f"Photon [red]{name}[/] does not exist. Did you intend to run a local"
                " photon? If so, please specify --local.",
            )
            console.print(f"Running the most recent version of [green]{name}[/]: {id}")
        else:
            console.print(f"Running the specified version: [green]{id}[/]")
        # parse environment variables and secrets
        env_parsed, secret_parsed = _parse_env_and_secret_or_die(env, secret)
        mount_parsed = _parse_mount_or_die(workspace_url, auth_token, mount)
        deployment_name = _find_deployment_name_or_die(
            workspace_url, auth_token, name, id, deployment_name
        )
        resource_shape = _validate_resource_shape(resource_shape)
        final_tokens = _parse_deployment_tokens_or_die(public, tokens)
        response = api.run_remote(
            workspace_url,
            auth_token,
            id,
            deployment_name,
            resource_shape,
            min_replicas,
            mount_parsed,
            env_parsed,
            secret_parsed,
            final_tokens,
        )
        explain_response(
            response,
            f"Photon launched as [green]{deployment_name}[/]. Use `lep deployment"
            f" status -n {deployment_name}` to check the status.",
            f"Failed to launch photon as [red]{deployment_name}[/]. See error"
            " message above.",
            f"Failed to launch photon as [red]{deployment_name}[/]. Internal server"
            " error.",
        )
    else:
        # local execution
        check(name or path, "Must specify either --name or --path.")
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
            console.print(
                f"Photon [yellow]{name_or_path}[/] does not exist, trying to create"
                " with --model."
            )
            check(
                name and model,
                "Must specify both --name and --model to create a new photon.",
            )
            ctx.invoke(create, name=name, model=model)
            path = find_local_photon(name)

        # envs: parse and set environment variables
        envs, _ = _parse_env_and_secret_or_die(env, {})
        for k, v in envs.items():
            os.environ[k] = v
        if mount or secret or tokens:
            console.print(
                "Mounts, secrets and access tokens are only supported for"
                " remote execution. They will be ignored for local execution."
            )

        metadata = api.load_metadata(path)

        if metadata.get(METADATA_VCS_URL_KEY, None):
            workpath = fetch_code_from_vcs(metadata[METADATA_VCS_URL_KEY])
            os.chdir(workpath)
        photon = api.load(path)

        port = _find_available_port(port)
        console.print(f"Launching photon on port: [green]{port}[/]")
        photon.launch(port=port)
        return


@photon.command(hidden=True)
@click.option("--file", "-f", "path", help="Path to .photon file")
@click.pass_context
def prepare(ctx, path):
    """
    Prepare the environment for running a photon. This is only used by the
    platform to prepare the environment inside the container and not meant to
    be used by users.
    """
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
@click.option("--name", "-n", help="Name of the photon", required=True)
def push(name):
    """
    Push a photon to the workspace.
    """
    workspace_url, auth_token = get_workspace_and_token_or_die()
    path = find_local_photon(name)
    check(path and os.path.exists(path), f"Photon [red]{name}[/] does not exist.")
    response = api.push(workspace_url, auth_token, path)
    explain_response(
        response,
        f"Photon [green]{name}[/] pushed to workspace.",
        f"Photon [red]{name}[/] failed to push.",
        f"Photon [red]{name}[/] failed to push. Internal server error.",
    )


@photon.command()
@click.option("--id", "-i", help="ID of the photon", required=True)
@click.option("--file", "-f", "path", help="Path to the local .photon file")
def fetch(id, path):
    """
    Fetch a photon from the workspace.
    """
    workspace_url, auth_token = get_workspace_and_token_or_die()
    photon_or_err = api.fetch(workspace_url, auth_token, id, path)
    if isinstance(photon_or_err, APIError):
        console.print(f"Photon [red]{id}[/] failed to fetch: {photon_or_err}")
        sys.exit(1)
    console.print(f"Photon [green]{photon_or_err.name}:{id}[/] fetched.")


def add_command(cli_group):
    cli_group.add_command(photon)
