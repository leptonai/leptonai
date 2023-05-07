import json
import os
import requests
from typing import Any
import zipfile
from .base import schema_registry, type_registry, Photon, add_photon
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
    with open(path, 'rb') as file:
        response = requests.post(url + "/photons", files={'file': file})
        response.raise_for_status()
