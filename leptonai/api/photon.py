import os
from typing import Any, Dict, List, Optional
import warnings

from leptonai.config import CACHE_DIR

# import leptonai.photon to register the schemas and types
import leptonai.photon  # noqa: F401
from leptonai.photon.base import (
    schema_registry,
    type_registry,
    BasePhoton,
    add_photon,
    remove_local_photon,
    find_all_local_photons,
)
from leptonai.util import check_photon_name

from .connection import Connection
from . import types
from .util import APIError, json_or_error
from .workspace import version


def create(name: str, model: Any) -> BasePhoton:
    """
    Create a photon from a model.

    :param str name: name of the photon
    :param Any model: model to create the photon from

    :return: the created photon
    :rtype: BasePhoton

    :raises ValueError: if the model is not supported
    """
    check_photon_name(name)

    def _find_creator(model: str):
        model_parts = model.split(":")
        schema = model_parts[0]
        return schema_registry.get(schema)

    if isinstance(model, str):
        creator = _find_creator(model)
        if creator is None:
            model = f"py:{model}"
            # default to Python Photon, try again with auto-filling schema
            creator = _find_creator(model)
        if creator is not None:
            return creator(name, model)
    else:
        for type_checker in type_registry.get_all():
            if type_checker(model):
                creator = type_registry.get(type_checker)
                return creator(name, model)

    raise ValueError(f"Failed to find Photon creator for name={name} and model={model}")


def save(photon: BasePhoton, path: Optional[str] = None) -> str:
    """
    Save a photon to a file. By default, the file is saved in the
    cache directory (``{CACHE_DIR} / {name}.photon``)

    :param BasePhoton photon: photon to save
    :param str path: path to save the photon to

    :return: path to the saved photon
    :rtype: str

    :raises FileExistsError: if the file already exists at the target path
    """
    return photon.save(path)


def load(path: str) -> BasePhoton:
    """
    Load a photon from a file.
    :param str path: path to the photon file

    :return: the loaded photon
    :rtype: BasePhoton
    """
    return BasePhoton.load(path)


def load_metadata(path: str, unpack_extra_files: bool = False) -> Dict[Any, Any]:
    """
    Load the metadata of a photon from a file.
    :param str path: path to the photon file
    :param bool unpack_extra_files: whether to unpack extra files

    :return: the metadata of the photon
    :rtype: dict
    """
    return BasePhoton.load_metadata(path, unpack_extra_files)


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
