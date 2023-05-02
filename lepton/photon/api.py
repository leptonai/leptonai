import json
import os
from typing import Any
import zipfile
from .base import schema_registry, type_registry, Photon, add_photon
from . import hf  # noqa: F401
from lepton.config import CACHE_DIR


def create(name: str, model: Any) -> Photon:
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


def save(photon, to: str = None):
    if to is None:
        to = CACHE_DIR / f"{photon.name}.photon"
    if os.path.exists(to):
        raise FileExistsError(f"Failed to save photon: file {to} already exists")
    with zipfile.ZipFile(to, "w") as f:
        f.writestr(
            "metadata.json",
            json.dumps(photon.metadata),
        )
        for name, file_path in photon.extra_files.items():
            f.write(os.path.join(photon.name, name), file_path)

        add_photon(photon.name, photon.model, to)
    return to


def load(path: str) -> Photon:
    with zipfile.ZipFile(path, "r") as f:
        # TODO: add registry to dispatch and pass the whole zip file
        # to corresponding creator
        with f.open("metadata.json") as config:
            metadata = json.load(config)
        photon = create(metadata["name"], metadata["model"])
        # TODO: load extra files
    return photon
