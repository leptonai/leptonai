import os

from lepton.db import DB
from lepton.registry import Registry


schema_registry = Registry()
type_registry = Registry()


class Photon:
    name: str
    model: str
    path: str

    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model

    @property
    def metadata(self):
        return {"name": self.name, "model": self.model}

    @property
    def extra_files(self):
        return {}

    def run(self, *args, **kwargs):
        raise NotImplementedError

    def run_as_server(self):
        raise NotImplementedError

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)

    def __str__(self):
        return f"Photon(name={self.name}, model={self.model})"


def add_photon(name: str, model: str, path: str):
    DB.cursor().execute(
        """INSERT INTO photon (name, model, path) VALUES (?, ?, ?)""",
        (name, model, str(path)),
    )
    DB.commit()


def find_all_photons():
    res = DB.cursor().execute("SELECT path FROM photon")
    paths = res.fetchall()
    return paths


def find_photon(name):
    res = DB.cursor().execute("SELECT path FROM photon WHERE name = ?", (name,))
    path_or_none = res.fetchone()
    if path_or_none is None:
        return None
    else:
        return path_or_none[0]


def remove_photon(name):
    res = DB.cursor().execute("SELECT path FROM photon WHERE name = ?", (name,))
    path_or_none = res.fetchone()
    if path_or_none is not None:
        path = path_or_none[0]
        if os.path.exists(path):
            os.remove(path)
    DB.cursor().execute("DELETE FROM photon WHERE name = ?", (name,))
    DB.commit()
