import click
import json

from rich.table import Table

from .util import (
    console,
    click_group,
    guard_api,
    get_connection_or_die,
    explain_response,
)
from leptonai.api import job as api
from leptonai.api.types import (
    LeptonJobSpec,
    LeptonJob,
    LeptonContainer,
    LeptonMetadata,
    VALID_SHAPES,
)


@click_group()
def job():
    """
    Manages Lepton Jobs.

    Jobs is an experimental feature. More details will be added soon.
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
    "--resource-shape",
    type=str,
    help="Resource shape for the deployment. Available types are: '"
    + "', '".join(VALID_SHAPES)
    + "'.",
    default=None,
)
@click.option(
    "--completions", type=int, help="Completion policy for the job.", default=None
)
@click.option("--parallelism", type=int, help="Parallelism for the job.", default=None)
@click.option(
    "--container-image", type=str, help="Container image for the job.", default=None
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
def create(
    name, file, resource_shape, completions, parallelism, container_image, port, command
):
    """
    Creates a job.
    """
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
    if resource_shape:
        job_spec.resource_shape = resource_shape
    if completions:
        job_spec.completions = completions
    if parallelism:
        job_spec.parallelism = parallelism
    if container_image or port or command:
        job_spec.container = LeptonContainer.make_container(
            image=container_image or job_spec.container.image,
            ports=port or job_spec.container.ports,
            command=command or job_spec.container.command,
        )

    job = LeptonJob(spec=job_spec, metadata=LeptonMetadata(id=name))
    conn = get_connection_or_die()
    guard_api(api.create_job(conn, job), detail=True)
    console.print(f"Job [green]{name}[/] created successfully.")


@job.command(name="list")
def list_command():
    """
    Lists all jobs in the current workspace.
    """
    conn = get_connection_or_die()
    jobs = guard_api(api.list_jobs(conn), detail=True)

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name")
    table.add_column("Created At")
    table.add_column("State (ready,active,succeeded,failed)")
    for job in jobs:
        status = job["status"]
        table.add_row(
            job["metadata"]["name"],
            job["metadata"]["creationTimestamp"],
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
