import os
from typing import List, Optional
import warnings

from leptonai.config import CACHE_DIR

# import leptonai.photon to register the schemas and types
import leptonai.photon  # noqa: F401
from leptonai.photon.base import (
    add_photon,
    remove_local_photon,
    find_all_local_photons,
)
from leptonai.photon.util import load

from .connection import Connection
from . import types
from .util import APIError, json_or_error
from .workspace import version


def push(conn: Connection, path: str):
    """
    Push a photon to a workspace.
    :param str path: path to the photon file
    """
    with open(path, "rb") as file:
        response = conn.post("/photons", files={"file": file})
        return response


def list_remote(conn: Connection):
    """
    List the photons on a workspace.
    """
    response = conn.get("/photons")
    return json_or_error(response)


def list_local():
    """
    List the photons in the local cache directory.
    """
    photons = find_all_local_photons()
    return [p[1] for p in photons]


def remove_remote(conn: Connection, id: str):
    """
    Remove a photon from a workspace.
    :param str id: id of the photon to remove
    """
    response = conn.delete("/photons/" + id)
    return response


def remove_local(name: str, remove_all: bool = False):
    return remove_local_photon(name, remove_all)


def fetch(conn: Connection, id: str, path: str):
    """
    Fetch a photon from a workspace.
    :param str id: id of the photon to fetch
    :param str path: path to save the photon to
    """
    if path is None:
        path = str(CACHE_DIR / f"tmp.{id}.photon")
        need_rename = True
    else:
        need_rename = False

    response = conn.get(
        "/photons/" + id + "?content=true",
        stream=True,
    )

    if response.status_code > 299:
        return APIError(response)

    with open(path, "wb") as f:
        f.write(response.content)

    photon = load(path)

    if need_rename:
        new_path = CACHE_DIR / f"{photon.name}.{id}.photon"
        os.rename(path, new_path)
    else:
        new_path = path

    # TODO: use remote creation time
    add_photon(id, photon.name, photon.model, str(new_path))

    return photon


def run_remote_with_spec(conn: Connection, deployment_spec: types.DeploymentSpec):
    """
    Run a photon on a workspace, with the given deployment spec.
    """
    response = conn.post("/deployments", json=deployment_spec.dict(exclude_none=True))
    return response


def run_remote(
    conn: Connection,
    id: str,
    deployment_name: str,
    resource_shape: str = types.DEFAULT_RESOURCE_SHAPE,
    resource_affinity: Optional[str] = None,
    min_replicas: int = 1,
    mounts: Optional[List[str]] = None,
    env_list: Optional[List[str]] = None,
    secret_list: Optional[List[str]] = None,
    is_public: Optional[bool] = False,
    tokens: Optional[List[str]] = None,
    no_traffic_timeout: Optional[int] = None,
):
    if no_traffic_timeout:
        ws_version = version(conn)
        if ws_version and ws_version < (0, 10, 0):
            warnings.warn(
                "no_traffic_timeout is not yet released on this workspace."
                " For now, your deployment will be created without timeout."
            )
    # TODO: check if the given id is a valid photon id
    deployment_spec = types.DeploymentSpec(
        name=deployment_name,
        photon_id=id,
        resource_requirement=types.ResourceRequirement.make_resource_requirement(
            resource_shape=resource_shape,
            resource_affinity=resource_affinity,
            min_replicas=min_replicas,
        ),
        mounts=types.Mount.make_mounts_from_strings(mounts),
        envs=types.EnvVar.make_env_vars_from_strings(env_list, secret_list),
        api_tokens=types.TokenVar.make_token_vars_from_config(is_public, tokens),
        auto_scaler=types.AutoScaler.make_auto_scaler(no_traffic_timeout),
    )
    return run_remote_with_spec(conn, deployment_spec)
