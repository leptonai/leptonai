from .connection import Connection
from .util import json_or_error
from .types import LeptonJob


def list_jobs(conn: Connection):
    """
    List all jobs on a workspace.
    """
    response = conn.get("/jobs")
    return json_or_error(response)


def create_job(conn: Connection, job: LeptonJob):
    """
    Create a job on a workspace.
    """
    response = conn.post("/jobs/", json=job.dict(exclude_none=True))
    return json_or_error(response)


def get_job(conn: Connection, name: str):
    """
    Get a job from a workspace.
    :param str id: id of the job to fetch
    """
    response = conn.get("/jobs/" + name)
    return json_or_error(response)


def update_job(conn: Connection, name: str, *args, **kwargs):
    """
    Update a job from a workspace.
    :param str id: id of the job to update
    """
    raise NotImplementedError("Job update is not implemented yet.")


def delete_job(conn: Connection, name: str):
    """
    Delete a job from a workspace.
    :param str id: id of the job to delete
    """
    response = conn.delete("/jobs/" + name)
    return response
