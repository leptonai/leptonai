import os
from typing import List, Optional, Dict, Any
import warnings

from leptonai.config import CACHE_DIR, ENV_VAR_REQUIRED

from loguru import logger

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


def fetch_metadata(conn: Connection, id: str):
    """
    Fetch the metadata of a photon fron a workspace.
    :param str id: id of the photon to fetch
    """
    response = conn.get("/photons/" + id)
    return json_or_error(response)


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

    # backward-compatibility: support the old style photon.name and photon.model,
    # and the newly updated photon._photon_name and photon._photon_model
    try:
        photon_name = photon._photon_name
        photon_model = photon._photon_model
    except AttributeError:
        photon_name = photon.name  # type: ignore
        photon_model = photon.model  # type: ignore

    if need_rename:
        new_path = CACHE_DIR / f"{photon_name}.{id}.photon"
        os.rename(path, new_path)
    else:
        new_path = path

    # TODO: use remote creation time
    add_photon(id, photon_name, photon_model, str(new_path))

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
    deployment_template: Optional[Dict[str, Any]] = None,
    resource_shape: Optional[str] = None,
    replica_cpu: Optional[float] = None,
    replica_memory: Optional[int] = None,
    replica_accelerator_type: Optional[str] = None,
    replica_accelerator_num: Optional[float] = None,
    replica_ephemeral_storage_in_gb: Optional[int] = None,
    resource_affinity: Optional[str] = None,
    min_replicas: int = 1,
    max_replicas: Optional[int] = None,
    mounts: Optional[List[str]] = None,
    env_list: Optional[List[str]] = None,
    secret_list: Optional[List[str]] = None,
    is_public: Optional[bool] = False,
    tokens: Optional[List[str]] = None,
    no_traffic_timeout: Optional[int] = None,
    target_gpu_utilization: Optional[int] = None,
    initial_delay_seconds: Optional[int] = None,
):
    # Deal with deployment template
    deployment_template = deployment_template or {}
    logger.trace(f"deployment_template:\n{deployment_template}")
    if resource_shape is None and "resource_shape" in deployment_template:
        resource_shape = deployment_template["resource_shape"]
    else:
        resource_shape = types.DEFAULT_RESOURCE_SHAPE
    template_envs = deployment_template.get("env", {})
    for k, v in template_envs.items():
        if v == ENV_VAR_REQUIRED:
            if not any(s.startswith(k + "=") for s in (env_list or [])):
                raise ValueError(
                    f"This deployment requires env var {k}, but it's missing."
                )
        else:
            env_list = env_list or []
            if not any(s.startswith(k + "=") for s in env_list):
                # Adding default env variable if not specified.
                env_list.append(f"{k}={v}")
    template_secrets = deployment_template.get("secret", [])
    for k in template_secrets:
        if not any(s.startswith(k) for s in (secret_list or [])) and not any(
            s.startswith(k) for s in (env_list or [])
        ):
            raise ValueError(f"This deployment requires secret {k}, but it's missing.")

    # TODO: check if the given id is a valid photon id
    deployment_spec = types.DeploymentSpec(
        name=deployment_name,
        photon_id=id,
        resource_requirement=types.ResourceRequirement.make_resource_requirement(
            resource_shape=resource_shape,
            replica_cpu=replica_cpu,
            replica_memory=replica_memory,
            replica_accelerator_type=replica_accelerator_type,
            replica_accelerator_num=replica_accelerator_num,
            replica_ephemeral_storage_in_gb=replica_ephemeral_storage_in_gb,
            resource_affinity=resource_affinity,
            min_replicas=min_replicas,
            max_replicas=max_replicas,
        ),
        mounts=types.Mount.make_mounts_from_strings(mounts),
        envs=types.EnvVar.make_env_vars_from_strings(env_list, secret_list),
        api_tokens=types.TokenVar.make_token_vars_from_config(is_public, tokens),
        auto_scaler=types.AutoScaler.make_auto_scaler(
            no_traffic_timeout, target_gpu_utilization
        ),
        health=types.HealthCheck.make_health_check(initial_delay_seconds),
    )

    logger.trace(f"deployment_spec:\n{deployment_spec}")
    return run_remote_with_spec(conn, deployment_spec)
