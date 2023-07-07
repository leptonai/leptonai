import json
import os
import zipfile

from leptonai.config import CACHE_DIR
from leptonai.db import DB
from leptonai.registry import Registry

schema_registry = Registry()
type_registry = Registry()
type_str_registry = Registry()


class BasePhoton:
    """Base class for all Photons."""

    photon_type = "base"
    """photon_type defines the type of the photon.
    It is used to identify the photon at building and deployment time.
    """

    extra_files = {}
    """Extra files that should be included in the photon.
    Extra files are files that are not part of the model source file, but are
    required to run the model. It takes two forms:
        - a dictionary of {remote_path: local_path} pairs, where the remote_path
          is relative to the cwd of the photon at runtime, and local_path is
          the path pointing to the file in the local file system. If local_path
          is relative, it is relative to the current working directory of the
          local environment.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for base in cls.__bases__:
            if issubclass(base, BasePhoton) and base.photon_type == cls.photon_type:
                # do not override load if its photon_type the same as parent class
                break
        else:
            type_str_registry.register(cls.photon_type, cls.load)

    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model

    def save(self, path: str = None):
        if path is None:
            # assuming maximum 1000 versions for now
            for version in range(1000):
                if version == 0:
                    path = CACHE_DIR / f"{self.name}.photon"
                else:
                    path = CACHE_DIR / f"{self.name}.{version}.photon"
                if not os.path.exists(path):
                    break
            else:
                raise ValueError(
                    f"Can not find a valid path for creating photon {self.name}"
                )
        with zipfile.ZipFile(path, "w") as f:
            metadata = self.metadata
            checked_extra_files = self._extra_files
            metadata["extra_files"] = list(checked_extra_files.keys())
            f.writestr(
                "metadata.json",
                json.dumps(metadata),
            )
            for name, path_or_content in checked_extra_files.items():
                if isinstance(path_or_content, bytes):
                    f.writestr(name, path_or_content)
                    continue
                elif isinstance(path_or_content, str):
                    if os.path.exists(path_or_content):
                        with open(path_or_content, "rb") as extra_file:
                            f.writestr(name, extra_file.read())
                    else:
                        f.writestr(name, path_or_content)
                else:
                    raise ValueError(
                        "extra_files value should be str or bytes, got"
                        f" {path_or_content}"
                    )

        # use path as local id for now
        add_photon(str(path), self.name, self.model, str(path))
        return path

    @staticmethod
    def load(path: str):
        metadata = BasePhoton.load_metadata(path, unpack_extra_files=True)
        photon_type = metadata["type"]
        photon_cls = type_str_registry.get(photon_type)
        if photon_cls is None:
            raise ValueError(
                f"Can not find Photon class for type '{photon_type}', please"
                " make sure the corresponding module is imported."
            )
        with zipfile.ZipFile(path, "r") as photon_file:
            photon = photon_cls(photon_file, metadata)
        return photon

    @staticmethod
    def load_metadata(path: str, unpack_extra_files: bool = False):
        with zipfile.ZipFile(path, "r") as photon_file:
            with photon_file.open("metadata.json") as config:
                metadata = json.load(config)
            if unpack_extra_files:
                for path in metadata["extra_files"]:
                    dirname = os.path.dirname(path)
                    if dirname:
                        os.makedirs(dirname, exist_ok=True)
                    with open(path, "wb") as out, photon_file.open(path) as extra_file:
                        out.write(extra_file.read())
        return metadata

    @property
    def metadata(self):
        return {"name": self.name, "model": self.model, "type": self.photon_type}

    @property
    def _extra_files(self):
        """
        Returns a dict of extra files to be included in the photon.

        If extra_files is a dict, it will be returned directly, with the keys being
        the file path in the photon, and the values being the file path in the buidling
        environment. If extra_files is a list, each list item should be a relative file
        path in the building environment, and the file will be included in the photon with the
        same name and path.
        """
        res = {}
        if isinstance(self.extra_files, list):
            # Verify if the file exists too.
            for path in self.extra_files:
                if not os.path.exists(path):
                    raise ValueError(
                        f"Can not find extra file {path} in the building environment"
                    )
                res[path] = path
        elif isinstance(self.extra_files, dict):
            res.update(self.extra_files)
        else:
            raise ValueError(
                f"extra_files should be either a dict or a list, got {self.extra_files}"
            )
        return res

    def __str__(self):
        return f"Photon(name={self.name}, model={self.model})"


def add_photon(id: str, name: str, model: str, path: str):
    DB.cursor().execute(
        """INSERT INTO photon (id, name, model, path, creation_time) VALUES (?, ?, ?, ?, strftime('%s','now'))""",
        (id, name, model, path),
    )
    DB.commit()


def find_all_local_photons():
    res = DB.cursor().execute("SELECT * FROM photon ORDER BY creation_time DESC")
    records = res.fetchall()
    return records


def find_local_photon(name):
    res = DB.cursor().execute(
        "SELECT * FROM photon WHERE name = ? ORDER BY creation_time DESC", (name,)
    )
    record_or_none = res.fetchone()
    if record_or_none is None:
        return None
    else:
        return record_or_none[0]


def remove_local_photon(name):
    res = DB.cursor().execute(
        "SELECT path FROM photon WHERE name = ? ORDER BY creation_time DESC", (name,)
    )
    path_or_none = res.fetchone()
    if path_or_none is None:
        return
    path = path_or_none[0]
    if os.path.exists(path):
        os.remove(path)
    DB.cursor().execute("DELETE FROM photon WHERE name = ? AND path = ?", (name, path))
    DB.commit()
