import click
from datetime import datetime
import json
import sys

from loguru import logger
from rich.table import Table

from .util import (
    console,
    click_group,
    catch_deprecated_flag,
    check,
    _get_valid_nodegroup_ids,
    _get_valid_node_ids,
)
from leptonai.api.v1.photon import make_mounts_from_strings, make_env_vars_from_strings
from leptonai.config import BASE_IMAGE, VALID_SHAPES

from leptonai.api.v1.types.common import Metadata
from leptonai.api.v1.types.job import (
    LeptonJob,
    LeptonJobUserSpec,
    LeptonResourceAffinity,
)
from leptonai.api.v1.types.deployment import ContainerPort, LeptonLog
from leptonai.api.v1.client import APIClient


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


def make_container_port_from_string(port_str: str):
    parts = port_str.split(":")
    if len(parts) == 2:
        try:
            port = int(parts[0].strip())
        except ValueError:
            raise ValueError(
                f"Invalid port definition: {port_str}. Port must be an integer."
            )
        return ContainerPort(container_port=port, protocol=parts[1].strip())
    else:
        raise ValueError(f"Invalid port definition: {port_str}")


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
# --contianer-image, --container-port (--port), --command defines the container spec.
@click.option(
    "--container-image",
    type=str,
    help=(
        "Container image for the job. If not set, default to leptonai.config.BASE_IMAGE"
    ),
    default=None,
)
@click.option(
    "--container-port",
    type=str,
    help="Ports to expose for the job, in the format portnumber[:protocol].",
    multiple=True,
)
@click.option(
    "--port",
    "container_port",
    type=str,
    callback=catch_deprecated_flag("port", "container-port"),
    help="Deprecated flag, use --container-port instead.",
    multiple=True,
)
@click.option(
    "--command", type=str, help="Command string to run for the job.", default=None
)
@click.option(
    "--resource-shape",
    type=str,
    help="Resource shape for the pod. Available types are: '"
    + "', '".join(VALID_SHAPES)
    + "'.",
    default=None,
)
@click.option(
    "--node-group",
    "-ng",
    "node_groups",
    help=(
        "Node group for the job. If not set, use on-demand resources. You can repeat"
        " this flag multiple times to choose multiple node groups. Multiple node group"
        " option is currently not supported but coming soon for enterprise users. Only"
        " the first node group will be set if you input multiple node groups at this"
        " time."
    ),
    type=str,
    multiple=True,
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
    "--max-failure-retry",
    type=int,
    help="Maximum number of failures to retry per worker.",
    default=None,
)
@click.option(
    "--max-job-failure-retry",
    type=int,
    help="Maximum number of failures to retry per whole job.",
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
        "Persistent storage to be mounted to the job, in the format"
        " `STORAGE_PATH:MOUNT_PATH`."
    ),
    multiple=True,
)
@click.option(
    "--image-pull-secrets",
    type=str,
    help="Secrets to use for pulling images.",
    multiple=True,
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
    "--privileged",
    type=bool,
    is_flag=True,
    help="Run the job in privileged mode.",
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
@click.option(
    "--log-collection",
    "-lg",
    type=bool,
    help=(
        "Enable or disable log collection (true/false). If not provided, the workspace"
        " setting will be used."
    ),
)
@click.option(
    "--node-id",
    "-ni",
    "node_ids",
    help=(
        "Node for the job. You can repeat this flag multiple times to choose multiple"
        " nodes. Please specify the node group when you are using this option"
    ),
    type=str,
    multiple=True,
)
def create(
    name,
    file,
    container_image,
    container_port,
    command,
    resource_shape,
    node_groups,
    num_workers,
    max_failure_retry,
    max_job_failure_retry,
    env,
    secret,
    mount,
    image_pull_secrets,
    intra_job_communication,
    privileged,
    ttl_seconds_after_finished,
    log_collection,
    node_ids,
):
    """
    Creates a job.

    For advanced uses, check https://kubernetes.io/docs/concepts/workloads/controllers/job/.
    """

    client = APIClient()
    if file:
        try:
            with open(file, "r") as f:
                content = f.read()
                job_spec = LeptonJobUserSpec.parse_raw(content)
        except Exception as e:
            console.print(f"Cannot load job spec from file [red]{file}[/]: {e}")
            return
    else:
        job_spec = LeptonJobUserSpec()
    # Update the spec based on the passed in args
    if node_groups:
        node_group_ids = _get_valid_nodegroup_ids(node_groups)
        # _get_valid_node_ids will return None if node_group_ids is None
        valid_node_ids = _get_valid_node_ids(node_group_ids, node_ids)
        # make sure affinity is initialized
        job_spec.affinity = job_spec.affinity or LeptonResourceAffinity()
        job_spec.affinity = LeptonResourceAffinity(
            allowed_dedicated_node_groups=node_group_ids,
            allowed_nodes_in_node_group=valid_node_ids,
        )
    if resource_shape:
        job_spec.resource_shape = resource_shape
    if num_workers:
        job_spec.completions = num_workers
        job_spec.parallelism = num_workers
        job_spec.intra_job_communication = True
    else:
        if intra_job_communication:
            job_spec.intra_job_communication = intra_job_communication
    if max_failure_retry:
        job_spec.max_failure_retry = max_failure_retry
    if max_job_failure_retry:
        job_spec.max_job_failure_retry = max_job_failure_retry
    if command:
        # For CLI passed in command, we will prepend it with /bin/bash -c
        command = ["/bin/bash", "-c", command]
        job_spec.container.command = command
    elif not job_spec.container.command:
        console.print("You did not specify a command to run the job.")
        sys.exit(1)
    if container_image:
        job_spec.container.image = container_image
    elif not job_spec.container.image:
        job_spec.container.image = BASE_IMAGE
    if container_port:
        job_spec.container.ports = [
            make_container_port_from_string(p) for p in container_port
        ]
    if env or secret:
        job_spec.envs = make_env_vars_from_strings(env, secret)  # type: ignore
    if mount:
        job_spec.mounts = make_mounts_from_strings(mount)  # type: ignore
    if image_pull_secrets:
        job_spec.image_pull_secrets = image_pull_secrets
    if privileged:
        job_spec.privileged = privileged
    if ttl_seconds_after_finished:
        job_spec.ttl_seconds_after_finished = ttl_seconds_after_finished
    if log_collection is not None:
        job_spec.log = LeptonLog(enable_collection=log_collection)
    if not job_spec.resource_shape:
        available_types = "\n      ".join(VALID_SHAPES)
        console.print(
            "[red]Error: Missing option '--resource-shape'.[/] "
            f"Available types are:\n      {available_types}. \n"
        )
        sys.exit(1)

    job = LeptonJob(spec=job_spec, metadata=Metadata(id=name))

    logger.trace(json.dumps(job.model_dump(), indent=2))
    created_job = client.job.create(job)
    new_job_id = created_job.metadata.id_
    console.print(f"Job [green]{name}  : id: {new_job_id}[/] created successfully.")


@job.command(name="list")
def list_command():
    """
    Lists all jobs in the current workspace.
    """
    client = APIClient()
    jobs = client.job.list_all()
    logger.trace(f"Jobs: {jobs}")

    table = Table(show_header=True)
    table.add_column("Name")
    table.add_column("ID")
    table.add_column("Created At")
    table.add_column("State (ready,active,succeeded,failed)")
    for job in jobs:
        status = job.status
        table.add_row(
            job.metadata.name,
            job.metadata.id_,
            (
                datetime.fromtimestamp(job.metadata.created_at / 1000).strftime(
                    "%Y-%m-%d\n%H:%M:%S"
                )
                if job.metadata.created_at
                else "N/A"
            ),
            f"{status.state} ({status.ready},{status.active},{status.succeeded},{status.failed})",
        )
    table.title = "Jobs"
    console.print(table)


@job.command()
@click.option("--name", "-n", help="Job name", type=str, required=False)
@click.option("--id", "-i", help="Job id", type=str, required=False)
def get(name, id):
    """
    Gets the job with the given name.
    """
    if not name and not id:
        raise click.UsageError("You must provide either --name or --id.")
    if name and id:
        raise click.UsageError(
            "You cannot provide both --name and --id. Please specify only one."
        )

    client = APIClient()
    target_jobs = []

    if id:
        job = client.job.get(id)
        target_jobs.append(job)

    if name:
        jobs = client.job.list_all()
        for job in jobs:
            if job.metadata.name == name:
                target_jobs.append(job)

    console.print(f"Job details for [green]{name or id}[/]:")
    for job in target_jobs:
        console.print(json.dumps(client.job.safe_json(job), indent=2))
        console.print("--------------------------\n")


@job.command()
@click.option(
    "--id", "-i", help="The ID of the job to remove.", type=str, required=False
)
@click.option(
    "--name",
    "-n",
    help=(
        "The name of the job to remove. If multiple jobs share the same name, all of"
        " them will be removed."
    ),
    required=False,
)
def remove(id, name):
    """
    Removes the job with the given name.
    """
    if not name and not id:
        raise click.UsageError("You must provide either --name or --id.")
    if name and id:
        raise click.UsageError(
            "You cannot provide both --name and --id. Please specify only one."
        )

    client = APIClient()

    target_job_ids = []
    if id:
        target_job_ids.append(id)

    if name:
        jobs = client.job.list_all()
        for job in jobs:
            if job.metadata.name == name:
                target_job_ids.append(job.metadata.id_)

    for job_id in target_job_ids:
        client.job.delete(job_id)
        console.print(f"Job [green]{job_id}[/] deleted successfully.")


@job.command()
@click.option("--id", "-i", help="The job id to get log.", required=True)
@click.option("--replica", "-r", help="The replica name to get log.", default=None)
def log(id, replica):
    """
    Gets the log of a job. If `replica` is not specified, the first replica
    is selected. Otherwise, the log of the specified replica is shown. To get the
    list of replicas, use `lep job status`.
    """
    client = APIClient()

    if not replica:
        # obtain replica information, and then select the first one.
        console.print(
            f"Replica name not specified for [yellow]{id}[/]. Selecting the first"
            " replica."
        )

        replicas = client.job.get_replicas(id)
        check(len(replicas) > 0, f"No replicas found for [red]{id}[/].")
        replica = replicas[0].metadata.id_
        console.print(f"Selected replica [green]{replica}[/].")
    else:
        console.print(f"Showing log for replica [green]{replica}[/].")
    stream_or_err = client.job.get_log(id_or_job=id, replica=replica)
    # Print the log as a continuous stream until the user presses Ctrl-C.
    try:
        for chunk in stream_or_err:
            console.print(chunk, end="")
    except KeyboardInterrupt:
        console.print("Disconnected.")
    except Exception:
        console.print("Connection stopped.")
        return
    else:
        console.print(
            "End of log. It seems that the job has not started, or already finished."
        )
        console.print(f"Use `lep job status -n {id}` to check the status of the job.")


@job.command()
@click.option("--id", "-i", help="The job id to get replicas.", required=True)
def replicas(id):

    client = APIClient()

    replicas = client.job.get_replicas(id)

    table = Table(show_header=True, show_lines=False)
    table.add_column("job name")
    table.add_column("replica id")

    for replica in replicas:
        table.add_row(id, replica.metadata.id_)
    console.print(table)


@job.command()
@click.option("--id", "-i", help="The job id to get events.", required=True)
def events(id, replica=None):

    client = APIClient()

    events = client.job.get_events(id)

    table = Table(title="Job Events", show_header=True, show_lines=False)
    table.add_column("Job Name")
    table.add_column("Type")
    table.add_column("Reason")
    table.add_column("Regarding")
    table.add_column("Count")
    table.add_column("Last Observed Time")
    for event in events:
        date_string = event.last_observed_time.strftime("%Y-%m-%d %H:%M:%S")
        table.add_row(
            id,
            event.type_,
            event.reason,
            str(event.regarding),
            str(event.count),
            date_string,
        )
    console.print(table)


def add_command(cli_group):
    cli_group.add_command(job)
