import json
import os
import requests
from typing import Any
import zipfile
from .base import schema_registry, type_registry, Photon, add_photon
from . import runner  # noqa: F401
from . import hf  # noqa: F401
from lepton.config import CACHE_DIR


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

    for type_ in type_registry.get_all():
        if isinstance(model, type_):
            creator = type_registry.get(type_)
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


def push(path, url: str):
    """
    Push a photon to a remote server.
    :param str path: path to the photon file
    :param str url: url of the remote server including the schema (e.g. http://localhost:8000)
    """
    with open(path, "rb") as file:
        response = requests.post(url + "/photons", files={"file": file})
        response.raise_for_status()


def list_remote(url: str):
    """
    List the photons on a remote server.
    :param str url: url of the remote server including the schema (e.g. http://localhost:8000)
    """
    response = requests.get(url + "/photons")
    response.raise_for_status()
    return response.json()

def remove_remote(url:str, id: str):
    """
    Remove a photon from a remote server.
    :param str url: url of the remote server including the schema (e.g. http://localhost:8000)
    :param str id: id of the photon to remove
    """
    response = requests.delete(url + "/photons/" + id)
    if response.status_code == 404:return False
    response.raise_for_status()
    return True

def fetch(id: str, url: str, path: str):
    """
    Fetch a photon from a remote server.
    :param str id: id of the photon to fetch
    :param str url: url of the remote server including the schema (e.g. http://localhost:8000)
    :param str path: path to save the photon to
    """
    if path is None:
        path = CACHE_DIR / f"tmp.{id}.photon"
        need_rename = True 
    
    response = requests.get(url + "/photons/" + id + "?content=true", stream=True)
    response.raise_for_status()
    with open(path, "wb") as f:
        f.write(response.content)

    photon = load(path)
    
    if need_rename:
        new_path = CACHE_DIR / f"{photon.name}.{id}.photon"
        os.rename(path, new_path)
    
    # TODO: use remote creation time
    add_photon(id, photon.name, photon.model, str(new_path))

    return photon
