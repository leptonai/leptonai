from typing import Any, Dict, Optional
from leptonai.photon.base import schema_registry, BasePhoton

from leptonai.util import check_photon_name


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
