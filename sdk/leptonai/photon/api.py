import os
import requests
import sys
from typing import Any, Dict
from .base import schema_registry, type_registry, Photon, add_photon
from . import runner  # noqa: F401
from . import hf  # noqa: F401
from leptonai.config import CACHE_DIR
from leptonai.util import check_and_print_http_error


def create_header(auth_token: str) -> Dict[str, str]:
    """
    Generate HTTP header for a request given an auth token.
    :param str auth_token: auth token to use in the header
    :return: the generated HTTP header
    :rtype: dict[str, str]
    """
    return {"Authorization": "Bearer " + auth_token} if auth_token else {}


def create(name: str, model: Any) -> Photon:
    """
    Create a photon from a model.

    :param str name: name of the photon
    :param Any model: model to create the photon from

    :return: the created photon
    :rtype: Photon

    :raises ValueError: if the model is not supported
    """
    if isinstance(model, str):
        model_parts = model.split(":")
        schema = model_parts[0]
        creator = schema_registry.get(schema)
        if creator is not None:
            return creator(name, model)

    for type_checker in type_registry.get_all():
        if type_checker(model):
            creator = type_registry.get(type_checker)
            return creator(name, model)

    raise ValueError(f"Failed to create photon: name={name}, model={model}")


def save(photon, path: str = None) -> str:
    """
    Save a photon to a file. By default, the file is saved in the
    cache directory (``{CACHE_DIR} / {name}.photon``)

    :param Photon photon: photon to save
    :param str path: path to save the photon to

    :return: path to the saved photon
    :rtype: str

    :raises FileExistsError: if the file already exists at the target path
    """
    return photon.save(path)


def load(path: str) -> Photon:
    """
    Load a photon from a file.
    :param str path: path to the photon file

    :return: the loaded photon
    :rtype: Photon
    """
    return Photon.load(path)


def load_metadata(path: str) -> Dict[Any, Any]:
    """
    Load the metadata of a photon from a file.
    :param str path: path to the photon file

    :return: the metadata of the photon
    :rtype: dict
    """
    return Photon.load_metadata(path)


def push(path, url: str, auth_token: str):
    """
    Push a photon to a remote server.
    :param str path: path to the photon file
    :param str url: url of the remote server including the schema
    (e.g. http://localhost:8000)
    """
    with open(path, "rb") as file:
        response = requests.post(url + "/photons", files={"file": file},
                                headers=create_header(auth_token)
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
    response = requests.get(
        url + "/photons", headers=create_header(auth_token))
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
        url + "/photons/" + id, headers=create_header(auth_token))
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

    response = requests.get(url + "/photons/" + id + "?content=true",
                            stream=True, headers=create_header(auth_token))
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


def remote_launch(id: str, url: str, cpu: float, memory: int, min_replicas: int, auth_token: str):
    # TODO: check if the given id is a valid photon id
    # TODO: get the photon name from the remote and use it as the deployment
    # name
    print(f"Launching photon {id}")
    deployment = {
        "name": f"deploy-{id[:6]}",
        "photon_id": id,
        "resource_requirement": {
            "cpu": cpu,
            "memory": memory,
            "min_replicas": min_replicas,
        },
    }
    response = requests.post(
        url + "/deployments", json=deployment, headers=create_header(auth_token))
    if check_and_print_http_error(response):
        sys.exit(1)
