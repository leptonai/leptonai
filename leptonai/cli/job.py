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
from leptonai.api.types import LeptonJobSpec, LeptonJob, LeptonMetadata


@click_group()
def job():
    """
    Manages Lepton Jobs.

    Jobs is an experimental feature. More details will be added soon.
    """
    pass


@job.command()
@click.option("--name", "-n", help="Job name", type=str, required=True)
@click.option("--file", "-f", help="Job spec file", type=str, required=True)
def create(name, file):
    """
    Creates a job from a job spec file.
    """
    try:
        with open(file, "r") as f:
            content = f.read()
            job_spec = LeptonJobSpec.parse_raw(content)
            job = LeptonJob(spec=job_spec, metadata=LeptonMetadata(id=name))
    except Exception as e:
        console.print(f"[red]Error[/]: {e}")
        return

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
    table.add_column("State")
    table.add_column("Ready")
    table.add_column("Active")
    table.add_column("Succeeded")
    table.add_column("Failed")
    for job in jobs:
        table.add_row(
            job["metadata"]["name"],
            job["metadata"]["creationTimestamp"],
            job["status"]["state"],
            str(job["status"]["ready"]),
            str(job["status"]["active"]),
            str(job["status"]["succeeded"]),
            str(job["status"]["failed"]),
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
