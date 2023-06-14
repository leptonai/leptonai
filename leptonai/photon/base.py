import json
import os
import zipfile

from leptonai.config import CACHE_DIR
from leptonai.db import DB
from leptonai.registry import Registry

schema_registry = Registry()
type_registry = Registry()
type_str_registry = Registry()


class Photon:
    photon_type = "base"
    extra_files = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for base in cls.__bases__:
            if issubclass(base, Photon) and base.photon_type == cls.photon_type:
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
            metadata["extra_files"] = list(self._extra_files.keys())
            f.writestr(
                "metadata.json",
                json.dumps(metadata),
            )
            for name, path_or_content in self._extra_files.items():
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
                        f"extra_files value should be str or bytes, got {path_or_content}"
                    )

        # use path as local id for now
        add_photon(str(path), self.name, self.model, str(path))
        return path

    @staticmethod
    def load(path: str):
        with zipfile.ZipFile(path, "r") as photon_file:
            with photon_file.open("metadata.json") as config:
                metadata = json.load(config)
            for path in metadata["extra_files"]:
                dirname = os.path.dirname(path)
                if dirname:
                    os.makedirs(dirname, exist_ok=True)
                with open(path, "wb") as out, photon_file.open(path) as extra_file:
                    out.write(extra_file.read())
            photon_type = metadata["type"]
            photon = type_str_registry.get(photon_type)(photon_file, metadata)
            return photon

    @staticmethod
    def load_metadata(path: str):
        with zipfile.ZipFile(path, "r") as photon_file:
            with photon_file.open("metadata.json") as config:
                metadata = json.load(config)
        return metadata

    @property
    def metadata(self):
        return {"name": self.name, "model": self.model, "type": self.photon_type}

    @property
    def _extra_files(self):
        res = {}
        extra_files = self.extra_files
        if not isinstance(extra_files, dict):
            raise ValueError(f"extra_files should be a dict, got {extra_files}")
        res.update(self.extra_files)
        return res

    def __str__(self):
        return f"Photon(name={self.name}, model={self.model})"


def add_photon(id: str, name: str, model: str, path: str):
    DB.cursor().execute(
        """INSERT INTO photon (id, name, model, path, creation_time) VALUES (?, ?, ?, ?, strftime('%s','now'))""",
        (id, name, model, path),
    )
    DB.commit()


def find_all_photons():
    res = DB.cursor().execute("SELECT * FROM photon ORDER BY creation_time DESC")
    records = res.fetchall()
    return records


def find_photon(name):
    res = DB.cursor().execute(
        "SELECT * FROM photon WHERE name = ? ORDER BY creation_time DESC", (name,)
    )
    record_or_none = res.fetchone()
    if record_or_none is None:
        return None
    else:
        return record_or_none[0]


def remove_photon(name):
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
