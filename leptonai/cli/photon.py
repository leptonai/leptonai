from datetime import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from typing import Optional, List, Tuple

from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table
import click

from leptonai.api.connection import Connection
from leptonai.api import photon as api
from leptonai.api import types
from leptonai.api.deployment import list_deployment, remove_deployment
from leptonai.api.workspace import WorkspaceInfoLocalRecord
from leptonai.api.secret import create_secret, list_secret
from leptonai import config
from leptonai.photon import util as photon_util
from leptonai.photon import Photon
from leptonai.photon.base import (
    find_all_local_photons,
    find_local_photon,
    remove_local_photon,
)
from leptonai.photon.constants import METADATA_VCS_URL_KEY
from leptonai.photon.download import fetch_code_from_vcs
from leptonai.util import find_available_port

from .util import (
    click_group,
    guard_api,
    check,
    get_connection_or_die,
    explain_response,
    APIError,
)


console = Console(highlight=False)


def _get_ordered_photon_ids_or_none(
    conn: Connection, name: str, public_photon: bool
) -> Optional[List[str]]:
    """Returns a list of photon ids for a given name, in the order newest to
    oldest. If no photon of such name exists, returns None.
    """
    photons = api.list_remote(conn, public_photon=public_photon)
    guard_api(photons, msg=f"Failed to list photons in workspace [red]{conn._url}[/].")
    target_photons = [p for p in photons if p["name"] == name]  # type: ignore
    if len(target_photons) == 0:
        return None
    target_photons.sort(key=lambda p: p["created_at"], reverse=True)
    return [p["id"] for p in target_photons]


def _get_most_recent_photon_id_or_none(
    conn: Connection, name: str, public_photon: bool
) -> Optional[str]:
    """Returns the most recent photon id for a given name. If no photon of such
    name exists, returns None.
    """
    photon_ids = _get_ordered_photon_ids_or_none(conn, name, public_photon)
    return photon_ids[0] if photon_ids else None


def _create_workspace_token_secret_var_if_not_existing(conn: Connection):
    """
    Adds the workspace token as a secret environment variable.
    """
    workspace_token = WorkspaceInfoLocalRecord.get_current_workspace_token() or ""
    existing_secrets = guard_api(
        list_secret(conn),
        msg="Failed to list secrets.",
    )
    if "LEPTON_WORKSPACE_TOKEN" not in existing_secrets:
        response = create_secret(conn, ["LEPTON_WORKSPACE_TOKEN"], [workspace_token])
        explain_response(
            response,
            None,
            "Failed to create secret LEPTON_WORKSPACE_TOKEN.",
            "Failed to create secret LEPTON_WORKSPACE_TOKEN.",
            exit_if_4xx=True,
        )


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
@click.option("--name", "-n", help="Name of the scaffolding file", default="main.py")
def scaffold(name: str):
    """
    Creates a scaffolding main.py file for a new photon. The file serves as a starting
    point that you can modify to create your own implementations. After implementing
    your photon, you can use `lep photon create -n [name] -m main.py` to create a
    photon from the file.
    """
    check(name.endswith(".py"), "Scaffolding file must end with .py")
    check(
        not os.path.exists(name),
        f"File {name} already exists. Please choose another name.",
    )
    from leptonai.photon.prebuilt import template

    shutil.copyfile(template.__file__, name)
    console.print(f"Created scaffolding file [green]{name}[/].")


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
        photon = photon_util.create(name=name, model=model)
    except Exception as e:
        console.print(f"Failed to create photon: [red]{e}[/]")
        sys.exit(1)
    try:
        photon_util.save(photon)
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
@click.option(
    "--public-photon",
    is_flag=True,
    help=(
        "If specified, remove the photon from the public photon registry. Note that"
        " public photons can only be managed by Lepton, so this option is hidden"
        " by default, but we provide this helpstring for documentation purposes."
    ),
    hidden=True,
    default=False,
)
def remove(name, local, id_, all_, public_photon):
    """
    Removes a photon. The behavior of this command depends on whether one has
    logged in to the Lepton AI cloud via `lep login`. If one has logged in, this
    command will remove the photon from the workspace. Otherwise, or of `--local`
    is explicitly specified, it will remove the photon from the local environment.
    """
    check(
        not (name and id_), "Cannot specify both --name and --id. Use one or the other."
    )
    check(name or id_, "Must specify either --name or --id.")
    check(
        not (public_photon and local),
        "Cannot specify --public-photon and --local both.",
    )

    if not local and WorkspaceInfoLocalRecord.get_current_workspace_id() is not None:
        # Remove remote photon.
        conn = WorkspaceInfoLocalRecord.get_current_connection()
        # Find ids that we need to remove
        if name:
            # Remove all versions of the photon.
            ids = _get_ordered_photon_ids_or_none(
                conn, name, public_photon=public_photon
            )
            check(ids, f"Cannot find photon with name [yellow]{name}[/].")
            ids = [ids[0]] if (not all_) else ids  # type: ignore
        else:
            ids = [id_]
        # Actually remove the ids
        for id_to_remove in ids:  # type: ignore
            explain_response(
                api.remove_remote(conn, id_to_remove, public_photon=public_photon),
                f"Photon id [green]{id_to_remove}[/] removed.",
                f"Photon id [red]{id_to_remove}[/] not removed. Some deployments"
                " may still be using it. Remove the deployments first with `lep"
                " deployment remove`.",
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


@photon.command(name="list")
@click.option("--local", "-l", help="If specified, list local photons", is_flag=True)
@click.option(
    "--pattern", help="Regular expression pattern to filter photon names", default=None
)
@click.option(
    "--public-photon",
    is_flag=True,
    help="If specified, list photons from the public photon registry.",
    default=False,
)
def list_command(local, pattern, public_photon):
    """
    Lists all photons. If one has logged in to the Lepton AI cloud via `lep login`,
    this command will list all photons in the Lepton AI cloud. Otherwise, or if
    `--local` is explicitly specified, it will list all photons in the local
    environment.
    """
    check(
        not (public_photon and local),
        "Cannot specify --public-photon and --local both.",
    )
    if not local and WorkspaceInfoLocalRecord.get_current_workspace_id() is not None:
        conn = WorkspaceInfoLocalRecord.get_current_connection()
        photons = guard_api(
            api.list_remote(conn, public_photon=public_photon),
            detail=True,
            msg=(
                "Failed to list photons in workspace"
                f" [red]{WorkspaceInfoLocalRecord.get_current_workspace_id()}[/]."
            ),
        )
        # Note: created_at returned by the server is in milliseconds, and as a
        # result we need to divide by 1000 to get seconds that is understandable
        # by the Python CLI.
        records = [
            (photon["name"], photon["model"], photon["id"], photon["created_at"] / 1000)
            for photon in photons
        ]
        ws_id = WorkspaceInfoLocalRecord.get_current_workspace_id()
        ws_name = WorkspaceInfoLocalRecord._get_current_workspace_display_name()
        if ws_name:
            title = f"Photons in workspace {ws_id}({ws_name})"
        else:
            title = f"Photons in workspace {ws_id}"
    else:
        records = find_all_local_photons()
        records = [
            (name, model, id_, creation_time)
            for id_, name, model, _, creation_time in records
        ]
        # We use current_workspace_id = None to indicate that we are in local mode.
        ws_id = None
        title = "Local Photons"

    table = Table(title=title, show_lines=True)
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
    if ws_id:
        console.print("To show local photons, use the `--local` flag.")


def _find_deployment_name_or_die(conn: Connection, name, id, deployment_name, rerun):
    deployments = guard_api(
        list_deployment(conn),
        detail=True,
        msg="Failed to list deployments.",
    )
    existing_names = set(d["name"] for d in deployments)
    if rerun:
        # Find the first fit deployment name, force remove deployment if it exists,
        # and return the name.
        if deployment_name is None:
            deployment_name = (name if name else id)[:32]
        if deployment_name in existing_names:
            console.print(f"Removing deployment {deployment_name}...")
            explain_response(
                remove_deployment(conn, deployment_name),
                f"Deployment {deployment_name} removed.",
                f"Failed to remove deployment {deployment_name}.",
                f"Failed to remove deployment {deployment_name}.",
                exit_if_4xx=True,
            )
            return deployment_name
    # otherwise, try find a new name.
    check(
        deployment_name not in existing_names,
        f"Deployment [red]{deployment_name}[/] already exists. please"
        " choose another name.",
    )
    if not deployment_name:
        console.print(
            "Attempting to find a proper deployment name. If you want to"
            " specify a name, please use the --deployment-name (or -dn for short)"
            " flag."
        )
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


def _timeout_must_be_larger_than_60(unused_ctx, unused_param, x):
    if x is None or x == 0 or x >= 60:
        return x
    else:
        raise click.BadParameter("Timeout value must be larger than 60 seconds.")


@photon.command()
@click.option("--name", "-n", type=str, help="Name of the photon to run.")
@click.option(
    "--model",
    "-m",
    type=str,
    help=(
        "Model spec of the photon. If model is specified, we will rebuild the photon"
        " before running."
    ),
)
@click.option(
    "--file", "-f", "path", type=str, help="Path to the specific `.photon` file to run."
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
@click.option(
    "--port", "-p", type=int, help="Port to run on.", default=config.DEFAULT_PORT
)
@click.option(
    "--id", "-i", type=str, help="ID of the photon (only required for remote)."
)
@click.option(
    "--resource-shape",
    type=str,
    help="Resource shape for the deployment. Available types are: '"
    + "', '".join(types.VALID_SHAPES)
    + "'.",
    default=None,
)
@click.option(
    "--replica-cpu",
    help="Resource CPU requirements per replica (experimental).",
    type=float,
    hidden=True,
    default=None,
)
@click.option(
    "--replica-memory",
    help="Resource memory requirements per replica (experimental).",
    type=int,
    hidden=True,
    default=None,
)
@click.option(
    "--replica-accelerator-type",
    help="Accelerator type requirement per replica (experimental).",
    type=str,
    hidden=True,
    default=None,
)
@click.option(
    "--replica-accelerator-num",
    help="Number of accelerators requirement per replica (experimental).",
    type=float,
    hidden=True,
    default=None,
)
@click.option(
    "--replica-ephemeral-storage-in-gb",
    help="Ephemeral storage requirement in GB per replica (experimental).",
    type=int,
    hidden=True,
    default=None,
)
@click.option(
    "--resource-affinity",
    help="Resource affinity (experimental).",
    type=str,
    hidden=True,
    default=None,
)
@click.option("--min-replicas", type=int, help="Minimum number of replicas.", default=1)
@click.option(
    "--max-replicas", type=int, help="Maximum number of replicas.", default=None
)
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
@click.option(
    "--no-traffic-timeout",
    type=int,
    help=(
        "If specified, the deployment will be scaled down to 0 replicas after the"
        " specified number of seconds without traffic. Minimum is 60 seconds if set."
        " Note that actual timeout may be up to 30 seconds longer than the specified"
        " value."
    ),
    callback=_timeout_must_be_larger_than_60,
)
@click.option(
    "--target-gpu-utilization",
    type=int,
    help=(
        "If min and max replicas are set, if the gpu utilization is higher than the"
        " target gpu utilization, autoscaler will scale up the replicas. If the gpu"
        " utilization is lower than the target gpu utilization, autoscaler will scale"
        " down the replicas. The value should be between 0 and 99."
    ),
    default=None,
)
@click.option(
    "--initial-delay-seconds",
    type=int,
    help=(
        "If specified, the deployment will allow the specified amount of seconds for"
        " the photon to initialize before it starts the service. Usually you should"
        " not need this. If you have a deployment that takes a long time to initialize,"
        " set it to a longer value."
    ),
    default=None,
)
@click.option(
    "--include-workspace-token",
    is_flag=True,
    help=(
        "If specified, the workspace token will be included as an environment"
        " variable. This is used when the photon code uses Lepton SDK capabilities such"
        " as queue, KV, objectstore etc. Note that you should trust the code in the"
        " photon, as it will have access to the workspace token."
    ),
    default=False,
)
@click.option(
    "--rerun",
    is_flag=True,
    help=(
        "If specified, shutdown the deployment of the same deployment name and"
        " rerun it. Note that this may cause downtime of the photon if it is for"
        " production use, so use with caution. In a production environment, you"
        " should do photon create, push, and `lep deployment update` instead."
    ),
    default=False,
)
@click.option(
    "--public-photon",
    is_flag=True,
    help=(
        "If specified, get the photon from the public photon registry. This is only"
        " supported for remote execution."
    ),
    default=False,
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
    replica_cpu,
    replica_memory,
    replica_accelerator_type,
    replica_accelerator_num,
    replica_ephemeral_storage_in_gb,
    resource_affinity,
    min_replicas,
    max_replicas,
    mount,
    deployment_name,
    env,
    secret,
    public,
    tokens,
    no_traffic_timeout,
    target_gpu_utilization,
    initial_delay_seconds,
    include_workspace_token,
    rerun,
    public_photon,
):
    """
    Runs a photon. If one has logged in to the Lepton AI cloud via `lep login`,
    the photon will be run on the cloud. Otherwise, or if `--local` is specified,
    the photon will be run locally.

    Refer to the documentation for a more detailed description on the choices
    among `--name`, `--model`, `--file` and `--id`.
    """
    check(not (name and id), "Must specify either --id or --name, not both.")
    check(
        not (public_photon and local),
        "Cannot specify --public-photon and --local both.",
    )
    check(not (public_photon and model), "Cannot specify --public and --model both.")

    if not local and WorkspaceInfoLocalRecord.get_current_workspace_id() is not None:
        # remote execution.
        conn = WorkspaceInfoLocalRecord.get_current_connection()
        if (name and model) and not id:
            console.print(
                f"Rebuilding photon with --model {model}.\nIf you want to run without"
                " rebuilding, please remove the --model arg."
            )
            ctx.invoke(create, name=name, model=model)
            ctx.invoke(push, name=name)
        # We first check if id is specified - this is the most specific way to
        # refer to a photon. If not, we will check if name is specified - this
        # might lead to multiple photons, so we will pick the latest one to run
        # as the default behavior.
        # TODO: Support push and run if the photon does not exist on remote
        if id is None:
            # look for the latest photon with the given name.
            id = _get_most_recent_photon_id_or_none(conn, name, public_photon)
            if not id:
                console.print(
                    f"Photon [red]{name}[/] does not exist in the workspace. Did"
                    " you intend to run a local photon? If so, please specify"
                    " --local.",
                )
                sys.exit(1)
            console.print(f"Running the most recent version of [green]{name}[/]: {id}")
        else:
            console.print(f"Running the specified version: [green]{id}[/]")

        if (
            no_traffic_timeout is None
            and config.DEFAULT_TIMEOUT
            and target_gpu_utilization is None
        ):
            console.print(
                "\nLepton is currently set to use a default timeout of [green]1"
                " hour[/]. This means that when there is no traffic for more than an"
                " hour, your deployment will automatically scale down to zero. This is"
                " to assist auto-release of unused debug deployments.\n- If you would"
                " like to run a long-running photon (e.g. for production), [green]set"
                " --no-traffic-timeout to 0[/].\n- If you would like to turn off"
                " default timeout, set the environment variable"
                " [green]LEPTON_DEFAULT_TIMEOUT=false[/].\n"
            )
            no_traffic_timeout = config.DEFAULT_TIMEOUT

        metadata = api.fetch_metadata(conn, id, public_photon=public_photon)  # type: ignore
        if isinstance(metadata, APIError):
            console.print(f"Photon [red]{name}[/] failed to fetch: {metadata}")
            sys.exit(1)
        deployment_template = metadata.get("deployment_template", None)  # type:ignore
        # parse environment variables and secrets
        deployment_name = _find_deployment_name_or_die(
            conn, name, id, deployment_name, rerun
        )

        if include_workspace_token:
            console.print("Including the workspace token for the photon execution.")
            _create_workspace_token_secret_var_if_not_existing(conn)
            if "LEPTON_WORKSPACE_TOKEN" not in secret:
                secret += ("LEPTON_WORKSPACE_TOKEN",)

        try:
            response = api.run_remote(
                conn,
                id,
                deployment_name,
                photon_namespace="public" if public_photon else "private",
                deployment_template=deployment_template,
                resource_shape=resource_shape,
                replica_cpu=replica_cpu,
                replica_memory=replica_memory,
                replica_accelerator_type=replica_accelerator_type,
                replica_accelerator_num=replica_accelerator_num,
                replica_ephemeral_storage_in_gb=replica_ephemeral_storage_in_gb,
                resource_affinity=resource_affinity,
                min_replicas=min_replicas,
                max_replicas=max_replicas,
                mounts=list(mount),
                env_list=list(env),
                secret_list=list(secret),
                is_public=public,
                tokens=tokens,
                no_traffic_timeout=no_traffic_timeout,
                target_gpu_utilization=target_gpu_utilization,
                initial_delay_seconds=initial_delay_seconds,
            )
        except ValueError as e:
            console.print(
                f"Error encountered while processing deployment configs:\n[red]{e}[/]."
            )
            console.print("Failed to launch photon.")
            sys.exit(1)
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
        check(name or path, "Must specify either --name or --file.")
        if path is None:
            path = find_local_photon(name)
        # The criteria to rebuild photon: 1) photon does not exist, 2) model is explicitly specified
        if (not path or not os.path.exists(path)) or model:
            if not path or not os.path.exists(path):
                console.print(
                    f"Photon [yellow]{name if name is not None else path}[/] does not"
                    f" exist, trying to create with --model {model}."
                )
            else:
                console.print(
                    f"Rebuilding photon with --model {model}.\nIf you want to run"
                    " without rebuilding, please remove the --model arg."
                )
            check(
                name and model,
                "Must specify both --name and --model to create a new photon.",
            )
            ctx.invoke(create, name=name, model=model)
            path = find_local_photon(name)

        # envs: parse and set environment variables
        if env:
            env_parsed = types.EnvVar.make_env_vars_from_strings(env, [])
            for e in env_parsed if env_parsed else []:
                os.environ[e.name] = e.value if e.value else ""
        if secret:
            for secret_name in secret:
                if secret_name not in os.environ:
                    console.print(
                        f"You have specified a secret {secret_name} but it is not"
                        " defined in your environment. Local execution does not support"
                        " fetching secrets from the server. Please set the secret in"
                        " your environment as an env variable and try again."
                    )
        if mount or tokens:
            console.print(
                "Mounts, secrets and access tokens are only supported for"
                " remote execution. They will be ignored for local execution."
            )
        path = str(path)
        check(
            os.path.exists(path),
            f"You encountered an internal error: photon [red]{path}[/] does not exist.",
        )
        metadata = photon_util.load_metadata(path)

        if metadata.get(METADATA_VCS_URL_KEY, None):
            workpath = fetch_code_from_vcs(metadata[METADATA_VCS_URL_KEY])
            os.chdir(workpath)

        try:
            photon = api.load(path)
            port = find_available_port(port)
            console.print(f"Launching photon on port: [green]{port}[/]")
            if not isinstance(photon, Photon):
                console.print(
                    f"You encountered an unsupported path: Loaded Photon from {path}"
                    " is not a python runnable Photon object."
                )
                sys.exit(1)
            photon.launch(port=port)
        except ModuleNotFoundError:
            # We encountered a ModuleNotFoundError. This is likely due to missing
            # dependencies. We will print out a helpful message and exit.
            console.print(
                "While loading and launching photon, some modules are not found."
                " Details:\n"
            )
            traceback.print_exc()
            console.print(
                "\nIt seems that you are missing some dependencies. This is not a bug"
                " of LeptonAI library, and is due to the underlying photon requiring"
                " dependencies. When running photons locally, we intentionally refrain"
                " from installing these dependencies for you, in order to not mess with"
                " your local environment. You can manually install the missing"
                " dependencies by looking at the exception above."
            )
            if metadata["requirement_dependency"]:
                console.print(
                    "\nAccording to the photon's metadata, dependencies can be"
                    " installed via:\n\tpip install"
                    f" {' '.join(metadata['requirement_dependency'])}"
                )
            if metadata["system_dependency"]:
                console.print(
                    "\nAccording to the photon's metadata, system dependencies can be"
                    " installed via:\n\tsudo apt-get install"
                    f" {' '.join(metadata['system_dependency'])}"
                )
            console.print("Kindly install the dependencies and try again.")
            sys.exit(1)
        except Exception as e:
            console.print(
                f"Failed to launch photon: {type(e)}:"
                f" {e}\nTraceback:\n{traceback.format_exc()}"
            )
            sys.exit(1)
        return


def _sequentialize_pip_commands(commands: List[str]) -> List[Tuple[str, List[str]]]:
    """
    Sequentializes a list of pip commands to a sequence of installation and uninstallations.
    """
    chunks = []
    current_command = None
    current_list = []
    LEN_UNINSTALL_PREFIX = len("uninstall ")

    for lib in commands:
        if lib.startswith("uninstall "):
            lib = lib[LEN_UNINSTALL_PREFIX:].strip()
            command = "uninstall"
        else:
            lib = lib.strip()
            command = "install"
            # If the current command is different or hasn't been set yet
        if current_command != command:
            if current_list:
                # if there's any commands accumulated, add them to the chunks
                chunks.append((current_command, current_list))
            current_list = [lib]
            current_command = command
        else:
            # within the same installation/uninstallation group, we can safely
            # do dedup.
            if lib not in current_list:
                current_list.append(lib)

    # Adding any remaining commands
    if current_list:
        chunks.append((current_command, current_list))

    return chunks


@photon.command(hidden=True)
@click.option("--file", "-f", "path", help="Path to .photon file")
@click.pass_context
def prepare(ctx, path):
    """
    Prepare the environment for running a photon. This is only used by the
    platform to prepare the environment inside the container and not meant to
    be used by users.
    """
    metadata = photon_util.load_metadata(path, unpack_extra_files=True)

    if metadata.get(METADATA_VCS_URL_KEY, None):
        workpath = fetch_code_from_vcs(metadata[METADATA_VCS_URL_KEY])
        os.chdir(workpath)

    # Install system dependency before any python dependencies are installed.
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
        if sudo:
            confirmed = (not sys.stdin.isatty()) or Confirm.ask(
                f"Installing system dependency will run with sudo ({sudo}), continue?",
                default=True,
            )
        else:
            console.print("No `sudo` found in the system, try proceed without sudo.")
            confirmed = True

        if confirmed:
            console.print(f"Installing system_dependency:\n{system_dependency}")
            cmd_prefix = [sudo, apt] if sudo else [apt]
            try:
                subprocess.check_call(cmd_prefix + ["update"])
                subprocess.check_call(
                    cmd_prefix + ["install", "-y"] + system_dependency
                )
            except subprocess.CalledProcessError as e:
                console.print(f"Failed to {apt} install: {e}")
                sys.exit(1)

    # Installing requirement dependencies
    requirement_dependency = metadata.get("requirement_dependency", [])
    # breaking down to multiple pip install and uninstall phases, if there are
    # any dependencies to uninstall.
    pip_sequence = _sequentialize_pip_commands(requirement_dependency)
    for command, libraries in pip_sequence:
        console.print(f"pip {command}ing requirement_dependency:\n{libraries}")
        console.print(
            "First trying to install in one single command to speed up installation."
        )
        with tempfile.NamedTemporaryFile("w", suffix=".txt") as f:
            content = "\n".join(libraries)
            f.write(content)
            f.flush()
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", command, "-r", f.name]
                    + (["-y"] if command == "uninstall" else [])
                )
            except subprocess.CalledProcessError as e:
                console.print(f"Failed to pip {command} in one command: {e}")
                console.print("Trying to install one by one.")
                for lib in libraries:
                    try:
                        subprocess.check_call(
                            [sys.executable, "-m", "pip", command, lib]
                            + (["-y"] if command == "uninstall" else [])
                        )
                    except subprocess.CalledProcessError as e:
                        console.print(f"Failed to pip {command} {lib}: {e}")
                        sys.exit(1)
                console.print(f"Successfully pip {command}ed requirement_dependency.")


@photon.command()
@click.option("--name", "-n", help="Name of the photon", required=True)
@click.option(
    "--public-photon",
    is_flag=True,
    help=(
        "If specified, remove the photon from the public photon registry. Note that"
        " public photons can only be managed by Lepton, so this option is hidden"
        " by default, but we provide this helpstring for documentation purposes."
    ),
    hidden=True,
    default=False,
)
def push(name, public_photon):
    """
    Push a photon to the workspace.
    """
    conn = get_connection_or_die()
    path = find_local_photon(name)
    check(path and os.path.exists(path), f"Photon [red]{name}[/] does not exist.")
    response = api.push(conn, path, public_photon=public_photon)  # type: ignore
    explain_response(
        response,
        f"Photon [green]{name}[/] pushed to workspace.",
        f"Photon [yellow]{name}[/] already exists. Skipping pushing.",
        f"Photon [red]{name}[/] failed to push. Internal server error.",
    )


@photon.command()
@click.option("--name", "-n", help="Name of the photon", required=True)
@click.option(
    "--id",
    "-i",
    type=str,
    help=(
        "ID of the photon, if the photon is a remote one. If not specified, the latest"
        " photon will be used."
    ),
    default=None,
)
@click.option(
    "--local",
    "-l",
    is_flag=True,
    help="If specified, obtain metadata for the local photon.",
    default=False,
)
@click.option("--indent", type=int, help="Indentation of the json.", default=None)
@click.option(
    "--public-photon",
    is_flag=True,
    help=(
        "If specified, get the photon from the public photon registry. This is only"
        " supported for remote execution."
    ),
    default=False,
)
def metadata(name, id, local, indent, public_photon):
    """
    Returns the metadata json of the photon.
    """
    if local:
        check(id is None, "Cannot specify both --id and --local.")
        path = find_local_photon(name)
        check(path and os.path.exists(path), f"Photon [red]{name}[/] does not exist.")
        # loads the metadata
        metadata = photon_util.load_metadata(path)  # type: ignore
    else:
        conn = WorkspaceInfoLocalRecord.get_current_connection()
        if id is None:
            id = _get_most_recent_photon_id_or_none(conn, name, public_photon)
            check(id, f"Photon [red]{name}[/] does not exist.")
        metadata = api.fetch_metadata(conn, id, public_photon=public_photon)  # type: ignore
        if isinstance(metadata, APIError):
            console.print(f"Photon [red]{name}[/] failed to fetch: {metadata}")
            sys.exit(1)
    console.print(json.dumps(metadata, indent=indent))


@photon.command()
@click.option("--id", "-i", help="ID of the photon", required=True)
@click.option("--file", "-f", "path", help="Path to the local .photon file")
def fetch(id, path):
    """
    Fetch a photon from the workspace.
    """
    conn = get_connection_or_die()
    photon_or_err = api.fetch(conn, id, path)
    if isinstance(photon_or_err, APIError):
        console.print(f"Photon [red]{id}[/] failed to fetch: {photon_or_err}")
        sys.exit(1)
    else:
        # backward-compatibility: support the old style photon.name and photon.model,
        # and the newly updated photon._photon_name and photon._photon_model
        try:
            photon_name = photon_or_err._photon_name
        except AttributeError:
            photon_name = photon_or_err.name  # type: ignore
        console.print(f"Photon [green]{photon_name}:{id}[/] fetched.")


def add_command(cli_group):
    cli_group.add_command(photon)
    cli_group.add_command(run)
