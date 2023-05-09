import json
import os
import zipfile

from lepton.config import CACHE_DIR
from lepton.db import DB
from lepton.registry import Registry

schema_registry = Registry()
type_registry = Registry()
type_str_registry = Registry()


class Photon:
    photon_type = "base"

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
            f.writestr(
                "metadata.json",
                json.dumps(self.metadata),
            )
            for name, content in self.extra_files.items():
                file_path = os.path.join(name)
                f.writestr(file_path, content)

        add_photon(self.name, self.model, str(path))
        return path

    @staticmethod
    def load(path: str):
        with zipfile.ZipFile(path, "r") as photon_file:
            with photon_file.open("metadata.json") as config:
                metadata = json.load(config)
            photon_type = metadata["type"]
            photon = type_str_registry.get(photon_type)(photon_file, metadata)
            return photon

    @property
    def metadata(self):
        return {"name": self.name, "model": self.model, "type": self.photon_type}

    @property
    def extra_files(self):
        return {}

    def __str__(self):
        return f"Photon(name={self.name}, model={self.model})"


def add_photon(name: str, model: str, path: str):
    DB.cursor().execute(
        """INSERT INTO photon (id, name, model, path, creation_time) VALUES (?, ?, ?, ?, strftime('%s','now'))""",
        (path, name, model, path),  # use path as local id
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
