import click
from datetime import datetime
import json

from loguru import logger
from rich.table import Table

from .util import (
    console,
    click_group,
    guard_api,
    get_connection_or_die,
    explain_response,
)
from leptonai.api import job as api
from leptonai.api import nodegroup as nodegroup_api
from leptonai.api.types import (
    EnvVar,
    Mount,
    LeptonResourceAffinity,
    LeptonJobSpec,
    ContainerPort,
    LeptonJob,
    LeptonMetadata,
    VALID_SHAPES,
)
from leptonai.config import BASE_IMAGE


@click_group()
def job():
    """
    Manages Lepton Jobs.

    Lepton Jobs are for one-time and one-off tasks that run on one or more machines.
    For example, one can launch a shell script that does a bunch of data processing
    as a job, or a distributed ML training job over multiple, connected machines. See
    the documentation for more details.
    """
    pass


@job.command()
@click.option("--name", "-n", help="Job name", type=str, required=True)
@click.option(
    "--file",
    "-f",
    help=(
        "If specified, load the job spec from the file. Any explicitly passed in arg"
        " will update the spec based on the file."
    ),
    type=str,
)
@click.option(
    "--node-group",
    "-ng",
    "node_groups",
    help="Node group for the job. If not set, use on-demand resources.",
    type=str,
    multiple=True,
)
@click.option(
    "--resource-shape",
    type=str,
    help="Resource shape for the deployment. Available types are: '"
    + "', '".join(VALID_SHAPES)
    + "'.",
    default=None,
)
@click.option(
    "--num-workers",
    "-w",
    help=(
        "Number of workers to use for the job. For example, when you do a distributed"
        " training job of 4 replicas, use --num-workers 4."
    ),
    type=int,
    default=None,
)
@click.option(
    "--container-image",
    type=str,
    help=(
        "Container image for the job. If not set, default to leptonai.config.BASE_IMAGE"
    ),
    default=None,
)
@click.option(
    "--port",
    type=str,
    help="Ports to expose for the job, in the format portnumber[:protocol].",
    multiple=True,
)
@click.option(
    "--command", type=str, help="Command string to run for the job.", default=None
)
@click.option(
    "--intra-job-communication",
    type=bool,
    help=(
        "Enable intra-job communication. If --num-workers is set, this is automatically"
        " enabled."
    ),
    default=None,
)
@click.option(
    "--env",
    "-e",
    help="Environment variables to pass to the job, in the format `NAME=VALUE`.",
    multiple=True,
)
@click.option(
    "--secret",
    "-s",
    help=(
        "Secrets to pass to the job, in the format `NAME=SECRET_NAME`. If"
        " secret name is also the environment variable name, you can"
        " omit it and simply pass `SECRET_NAME`."
    ),
    multiple=True,
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
    "--completions",
    type=int,
    help=(
        "(advanced feature) completion policy for the job. This is supserceded by"
        " --num-workers if the latter is set."
    ),
    default=None,
)
@click.option(
    "--parallelism",
    type=int,
    help=(
        "(advanced feature) parallelism for the job. This is supserceded by"
        " --num-workers if the latter is set."
    ),
    default=None,
)
@click.option(
    "--ttl-seconds-after-finished",
    type=int,
    help=(
        "(advanced feature) limits the lifetime of a job that has finished execution"
        " (either Completed or Failed). If not set, we will have it default to 72"
        " hours. Ref:"
        " https://kubernetes.io/docs/concepts/workloads/controllers/job/#ttl-mechanism-for-finished-jobs"
    ),
    default=259200,
)
def create(
    name,
    file,
    node_groups,
    resource_shape,
    num_workers,
    container_image,
    port,
    command,
    intra_job_communication,
    env,
    secret,
    mount,
    completions,
    parallelism,
    ttl_seconds_after_finished,
):
    """
    Creates a job.

    For advanced uses, check https://kubernetes.io/docs/concepts/workloads/controllers/job/.
    """
    conn = get_connection_or_die()

    if file:
        try:
            with open(file, "r") as f:
                content = f.read()
                job_spec = LeptonJobSpec.parse_raw(content)
        except Exception as e:
            console.print(f"Cannot load job spec from file [red]{file}[/]: {e}")
            return
    else:
        job_spec = LeptonJobSpec()
    # Update the spec based on the passed in args
    if node_groups:
        node_group_ids = []
        valid_node_groups = {
            ng["metadata"]["name"]: ng["metadata"]["id"]
            for ng in guard_api(nodegroup_api.list_nodegroups(conn))
        }
        for ng in node_groups:
            if ng not in valid_node_groups:
                console.print(
                    f"Invalid node group: [red]{ng}[/] (valid node groups:"
                    f" {', '.join(valid_node_groups.keys())})"
                )
                return
            node_group_ids.append(valid_node_groups[ng])
        job_spec.affinity = LeptonResourceAffinity(
            allowed_dedicated_node_groups=node_group_ids
        )
    if resource_shape:
        job_spec.resource_shape = resource_shape
    if num_workers:
        job_spec.completions = num_workers
        job_spec.parallelism = num_workers
        job_spec.intra_job_communication = True
    else:
        if completions:
            job_spec.completions = completions
        if parallelism:
            job_spec.parallelism = parallelism
        if intra_job_communication:
            job_spec.intra_job_communication = intra_job_communication
    if command:
        # For CLI passed in command, we will prepend it with /bin/bash -c
        command = ["/bin/bash", "-c", command]
        job_spec.container.command = command
    elif not job_spec.container.command:
        console.print("You did not specify a command to run the job.")
    if container_image:
        job_spec.container.image = container_image
    elif not job_spec.container.image:
        job_spec.container.image = BASE_IMAGE
    if port:
        job_spec.container.ports = [
            ContainerPort.make_container_port_from_string(p) for p in port
        ]
    if env or secret:
        job_spec.env = EnvVar.make_env_vars(env, secret)
    if mount:
        job_spec.mounts = Mount.make_mounts_from_strings(mount)
    if ttl_seconds_after_finished:
        job_spec.ttl_seconds_after_finished = ttl_seconds_after_finished

    job = LeptonJob(spec=job_spec, metadata=LeptonMetadata(id=name))
    guard_api(api.create_job(conn, job), detail=True)
    console.print(f"Job [green]{name}[/] created successfully.")


@job.command(name="list")
def list_command():
    """
    Lists all jobs in the current workspace.
    """
    conn = get_connection_or_die()
    jobs = guard_api(api.list_jobs(conn), detail=True)

    logger.trace(f"Jobs: {jobs}")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name")
    table.add_column("Created At")
    table.add_column("State (ready,active,succeeded,failed)")
    for job in jobs:
        status = job["status"]
        table.add_row(
            job["metadata"]["id"],
            datetime.fromtimestamp(job["metadata"]["created_at"] / 1000).strftime(
                "%Y-%m-%d\n%H:%M:%S"
            ),
            f'{status["state"]} ({status["ready"]},{status["active"]},{status["succeeded"]},{status["failed"]})',
        )
    table.title = "Jobs"
    console.print(table)


@job.command()
@click.option("--name", "-n", help="Job name", type=str, required=True)
def get(name):
    """
    Gets the job with the given name.
    """
    conn = get_connection_or_die()
    job = guard_api(api.get_job(conn, name), detail=True)
    console.print(f"Job details for [green]{name}[/]:")
    console.print(json.dumps(job, indent=2))


@job.command()
@click.option("--name", "-n", help="Job name")
def remove(name):
    """
    Removes the job with the given name.
    """
    conn = get_connection_or_die()
    response = api.delete_job(conn, name)
    explain_response(
        response,
        f"Job [green]{name}[/] deleted successfully.",
        f"Job [yellow]{name}[/] does not exist.",
        f"{response.text}\nInternal error. See error message above.",
    )


def add_command(cli_group):
    cli_group.add_command(job)
