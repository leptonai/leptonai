import os
import requests
import sys
from typing import Any, Dict, List, Optional
from .base import schema_registry, type_registry, BasePhoton, add_photon
from . import photon  # noqa: F401
from . import hf  # noqa: F401
from leptonai.config import CACHE_DIR
from leptonai.util import create_header, check_and_print_http_error, check_photon_name


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


def save(photon: BasePhoton, path: str = None) -> str:
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


def load_metadata(path: str) -> Dict[Any, Any]:
    """
    Load the metadata of a photon from a file.
    :param str path: path to the photon file

    :return: the metadata of the photon
    :rtype: dict
    """
    return BasePhoton.load_metadata(path)


def push(path, url: str, auth_token: str):
    """
    Push a photon to a remote server.
    :param str path: path to the photon file
    :param str url: url of the remote server including the schema
    (e.g. http://localhost:8000)
    """
    with open(path, "rb") as file:
        response = requests.post(
            url + "/photons", files={"file": file}, headers=create_header(auth_token)
        )
        if check_and_print_http_error(response):
            sys.exit(1)
        return True


def list_remote(url: str, auth_token: str):
    """
    List the photons on a remote server.
    :param str url: url of the remote server including the schema
    (e.g. http://localhost:8000)
    """
    response = requests.get(url + "/photons", headers=create_header(auth_token))
    if check_and_print_http_error(response):
        sys.exit(1)
    return response.json()


def remove_remote(url: str, id: str, auth_token: str):
    """
    Remove a photon from a remote server.
    :param str url: url of the remote server including the schema
    (e.g. http://localhost:8000)
    :param str id: id of the photon to remove
    """
    response = requests.delete(
        url + "/photons/" + id, headers=create_header(auth_token)
    )
    if response.status_code == 404:
        return False
    if check_and_print_http_error(response):
        sys.exit(1)
    return True


def fetch(id: str, url: str, path: str, auth_token: str):
    """
    Fetch a photon from a remote server.
    :param str id: id of the photon to fetch
    :param str url: url of the remote server including the schema
    (e.g. http://localhost:8000)
    :param str path: path to save the photon to
    """
    if path is None:
        path = CACHE_DIR / f"tmp.{id}.photon"
        need_rename = True

    response = requests.get(
        url + "/photons/" + id + "?content=true",
        stream=True,
        headers=create_header(auth_token),
    )
    if check_and_print_http_error(response):
        sys.exit(1)

    with open(path, "wb") as f:
        f.write(response.content)

    photon = load(path)

    if need_rename:
        new_path = CACHE_DIR / f"{photon.name}.{id}.photon"
        os.rename(path, new_path)

    # TODO: use remote creation time
    add_photon(id, photon.name, photon.model, str(new_path))

    return photon


def remote_launch(
    id: str,
    url: str,
    cpu: float,
    memory: int,
    min_replicas: int,
    auth_token: str,
    mounts: Optional[List[str]] = None,
    deployment_name: Optional[str] = None,
    env_list: Optional[Dict[str, str]] = None,
    secret_list: Optional[Dict[str, str]] = None,
):
    # TODO: check if the given id is a valid photon id
    # TODO: get the photon name from the remote and use it as the deployment
    # name
    dn = deployment_name
    print(f"Launching photon {id}")
    if dn is None:
        dn = f"deploy-{id}"
        # format name to be valid
        dn = dn[:32] if len(dn) > 32 else dn
        if not dn[-1].isalnum():
            dn = dn[:-1] + "x"
        dn = dn.lower()

    envs_and_secrets = []
    for k, v in env_list.items():
        envs_and_secrets.append({"name": k, "value": v})
    for k, v in secret_list.items():
        envs_and_secrets.append({"name": k, "value_from": {"secret_name_ref": v}})
    deployment = {
        "name": dn,
        "photon_id": id,
        "resource_requirement": {
            "cpu": cpu,
            "memory": memory,
            "min_replicas": min_replicas,
        },
        "envs": envs_and_secrets,
        "mounts": mounts,
    }

    response = requests.post(
        url + "/deployments", json=deployment, headers=create_header(auth_token)
    )
    if check_and_print_http_error(response):
        sys.exit(1)
