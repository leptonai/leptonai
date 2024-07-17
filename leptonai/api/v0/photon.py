import os
from typing import List, Optional, Dict, Any
import warnings

from loguru import logger

from leptonai.config import (
    CACHE_DIR,
    ENV_VAR_REQUIRED,
    LEPTON_RESERVED_ENV_NAMES,
    DEFAULT_RESOURCE_SHAPE,
)

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


def _get_photon_endpoint(public_photon: bool) -> str:
    if public_photon:
        return "public"
    else:
        return "private"


def push(conn: Connection, path: str, public_photon: bool = False):
    """
    Push a photon to a workspace.
    :param str path: path to the photon file
    """
    with open(path, "rb") as file:
        response = conn.post(
            f"/photons/{_get_photon_endpoint(public_photon)}", files={"file": file}
        )
        return response


def list_remote(conn: Connection, public_photon: bool = False):
    """
    List the photons on a workspace.
    """
    response = conn.get(f"/photons/{_get_photon_endpoint(public_photon)}")
    return json_or_error(response)


def list_local():
    """
    List the photons in the local cache directory.
    """
    photons = find_all_local_photons()
    return [p[1] for p in photons]


def remove_remote(conn: Connection, id: str, public_photon: bool = False):
    """
    Remove a photon from a workspace.
    :param str id: id of the photon to remove
    """
    response = conn.delete(f"/photons/{_get_photon_endpoint(public_photon)}/" + id)
    return response


def remove_local(name: str, remove_all: bool = False):
    return remove_local_photon(name, remove_all)


def fetch_metadata(conn: Connection, id: str, public_photon: bool = False):
    """
    Fetch the metadata of a photon from a workspace.
    :param str id: id of the photon to fetch
    """
    response = conn.get(f"/photons/{_get_photon_endpoint(public_photon)}/" + id)
    return json_or_error(response)


def fetch(conn: Connection, id: str, path: str, public_photon: bool = False):
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
        f"/photons/{_get_photon_endpoint(public_photon)}/" + id + "?content=true",
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
    logger.trace(
        "Adding photon to local cache:"
        f" {id} {photon_name} {photon_model} {str(new_path)}"
    )
    add_photon(id, photon_name, photon_model, str(new_path))

    return photon


def run_remote_with_spec(conn: Connection, deployment_spec: types.Deployment):
    """
    Run a photon on a workspace, with the given deployment spec.
    """
    response = conn.post(
        "/deployments", json=deployment_spec.dict(exclude_none=True, by_alias=True)
    )
    return response


def make_mounts_from_strings(
    mounts: Optional[List[str]],
) -> Optional[List[types.Mount]]:
    """
    Parses a list of mount strings into a list of Mount objects.
    """
    if not mounts:
        return None
    mount_list = []
    for mount_str in mounts:
        parts = mount_str.split(":")
        if len(parts) == 2:
            # TODO: sanity check if the mount path exists.
            mount_list.append(
                types.Mount(path=parts[0].strip(), mount_path=parts[1].strip())
            )
        else:
            raise ValueError(f"Invalid mount definition: {mount_str}")
    return mount_list


def make_env_vars_from_strings(
    env: Optional[List[str]], secret: Optional[List[str]]
) -> Optional[List[types.EnvVar]]:
    if not env and not secret:
        return None
    env_list = []
    for s in env if env else []:
        try:
            k, v = s.split("=", 1)
        except ValueError:
            raise ValueError(f"Invalid environment definition: [red]{s}[/]")
        if k in LEPTON_RESERVED_ENV_NAMES:
            raise ValueError(
                "You have used a reserved environment variable name that is "
                "used by Lepton internally: {k}. Please use a different name. "
                "Here is a list of all reserved environment variable names:\n"
                f"{LEPTON_RESERVED_ENV_NAMES}"
            )
        env_list.append(types.EnvVar(name=k, value=v))
    for s in secret if secret else []:
        # We provide the user a shorcut: instead of having to specify
        # SECRET_NAME=SECRET_NAME, they can just specify SECRET_NAME
        # if the local env name and the secret name are the same.
        k, v = s.split("=", 1) if "=" in s else (s, s)
        if k in LEPTON_RESERVED_ENV_NAMES:
            raise ValueError(
                "You have used a reserved secret name that is "
                "used by Lepton internally: {k}. Please use a different name. "
                "Here is a list of all reserved environment variable names:\n"
                f"{LEPTON_RESERVED_ENV_NAMES}"
            )
        # TODO: sanity check if these secrets exist.
        env_list.append(
            types.EnvVar(name=k, value_from=types.EnvValue(secret_name_ref=v))
        )
    return env_list


def run_remote(
    conn: Connection,
    id: str,
    deployment_name: str,
    photon_namespace: Optional[str] = None,
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
    if resource_shape is None:
        resource_shape = deployment_template.get(
            "resource_shape", DEFAULT_RESOURCE_SHAPE
        )
    template_envs = deployment_template.get("env", {})
    for k, v in template_envs.items():
        if v == ENV_VAR_REQUIRED:
            if not any(s.startswith(k + "=") for s in (env_list or [])):
                warnings.warn(
                    f"This deployment requires env var {k}, but it's missing."
                    f" Please specify it with --env {k}=YOUR_VALUE. Otherwise, the"
                    " deployment may fail.",
                    RuntimeWarning,
                )
        else:
            env_list = list(env_list) if env_list is not None else []
            if not any(s.startswith(k + "=") for s in env_list):
                # Adding default env variable if not specified.
                env_list.append(f"{k}={v}")
    template_secrets = deployment_template.get("secret", [])
    for k in template_secrets:
        if not any(s.startswith(k) for s in (secret_list or [])) and not any(
            s.startswith(k) for s in (env_list or [])
        ):
            warnings.warn(
                f"This deployment requires secret {k}, but it's missing. Please set"
                f" the secret, and specify it with --secret {k}. Otherwise, the"
                " deployment may fail.",
                RuntimeWarning,
            )

    # TODO: check if the given id is a valid photon id
    from .deployment import make_token_vars_from_config

    deployment_user_spec = types.DeploymentUserSpec(
        photon_id=id,
        photon_namespace=photon_namespace,
        resource_requirement=types.ResourceRequirement(
            resource_shape=resource_shape,
            cpu=replica_cpu,
            memory=replica_memory,
            accelerator_type=replica_accelerator_type,
            accelerator_num=replica_accelerator_num,
            ephemeral_storage_in_gb=replica_ephemeral_storage_in_gb,
            affinity=(
                types.LeptonResourceAffinity(
                    allowed_dedicated_node_groups=[resource_affinity]
                )
                if resource_affinity
                else None
            ),
            min_replicas=min_replicas,
            max_replicas=max_replicas,
        ),
        mounts=make_mounts_from_strings(mounts),
        envs=make_env_vars_from_strings(env_list, secret_list),
        api_tokens=make_token_vars_from_config(is_public, tokens),
        auto_scaler=types.AutoScaler(
            scale_down=(
                types.ScaleDown(no_traffic_timeout=no_traffic_timeout)
                if no_traffic_timeout
                else None
            ),
            target_gpu_utilization_percentage=target_gpu_utilization,
        ),
        health=types.HealthCheck(
            liveness=(
                types.HealthCheckLiveness(initial_delay_seconds=initial_delay_seconds)
                if initial_delay_seconds
                else None
            )
        ),
    )
    deployment_spec = types.Deployment(
        metadata=types.Metadata(id=deployment_name, name=deployment_name),
        spec=deployment_user_spec,
    )

    logger.trace(f"deployment_spec:\n{deployment_spec}")
    return run_remote_with_spec(conn, deployment_spec)
