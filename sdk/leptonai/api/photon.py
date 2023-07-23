import os
import requests
from typing import Any, Dict, List, Optional, Union
from leptonai.photon.base import schema_registry, type_registry, BasePhoton, add_photon

# import leptonai.photon to register the schemas and types
import leptonai.photon  # noqa: F401
from leptonai.config import CACHE_DIR
from leptonai.util import check_photon_name
from .util import APIError, create_header, json_or_error


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


def push(url: str, auth_token: str, path: str):
    """
    Push a photon to a workspace.
    :param str url: url of the workspace including the schema
    (e.g. http://localhost:8000)
    :param str path: path to the photon file
    """
    with open(path, "rb") as file:
        response = requests.post(
            url + "/photons", files={"file": file}, headers=create_header(auth_token)
        )
        return response


def list_remote(url: str, auth_token: str):
    """
    List the photons on a workspace.
    :param str url: url of the workspace including the schema
    (e.g. http://localhost:8000)
    """
    response = requests.get(url + "/photons", headers=create_header(auth_token))
    return json_or_error(response)


def remove_remote(url: str, auth_token: str, id: str):
    """
    Remove a photon from a workspace.
    :param str url: url of the workspace including the schema
    (e.g. http://localhost:8000)
    :param str id: id of the photon to remove
    """
    response = requests.delete(
        url + "/photons/" + id, headers=create_header(auth_token)
    )
    return response


def fetch(url: str, auth_token: str, id: str, path: str):
    """
    Fetch a photon from a workspace.
    :param str url: url of the workspace including the schema
    (e.g. http://localhost:8000)
    :param str id: id of the photon to fetch
    :param str path: path to save the photon to
    """
    if path is None:
        path = str(CACHE_DIR / f"tmp.{id}.photon")
        need_rename = True
    else:
        need_rename = False

    response = requests.get(
        url + "/photons/" + id + "?content=true",
        stream=True,
        headers=create_header(auth_token),
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


def run_remote(
    url: str,
    auth_token: str,
    id: str,
    deployment_name: str,
    resource_shape: str,
    min_replicas: int,
    mounts: Optional[List[str]] = None,
    env_list: Optional[Dict[str, str]] = None,
    secret_list: Optional[Dict[str, str]] = None,
    tokens: Optional[List[Dict[str, Union[str, Dict[str, str]]]]] = None,
):
    # TODO: check if the given id is a valid photon id
    envs_and_secrets = []
    for k, v in env_list.items():
        envs_and_secrets.append({"name": k, "value": v})
    for k, v in secret_list.items():
        envs_and_secrets.append({"name": k, "value_from": {"secret_name_ref": v}})
    deployment = {
        "name": deployment_name,
        "photon_id": id,
        "resource_requirement": {
            "resource_shape": resource_shape,
            "min_replicas": min_replicas,
        },
        "envs": envs_and_secrets,
        "mounts": mounts,
        "api_tokens": tokens,
    }

    response = requests.post(
        url + "/deployments", json=deployment, headers=create_header(auth_token)
    )
    return response
