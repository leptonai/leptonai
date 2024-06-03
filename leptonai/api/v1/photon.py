import os
from typing import List, Union, Optional

from loguru import logger

from leptonai.config import CACHE_DIR
from leptonai.photon.util import load
from leptonai.photon.base import (
    add_photon,
    remove_local_photon,
    find_all_local_photons,
)

from .common import APIResourse
from .types.photon import Photon as Photon
from .types.deployment import LeptonDeployment


def _get_photon_endpoint(public_photon: bool) -> str:
    """
    Based on the public_photon flag, return the correct endpoint path segment.
    """
    if public_photon:
        return "public"
    else:
        return "private"


class PhotonAPI(APIResourse):
    def list_all(self, public_photon: bool = False) -> List[Photon]:
        """
        List all photons on the workspace.
        """
        response = self._get(f"/photons/{_get_photon_endpoint(public_photon)}")
        return self._ws.ensure_list(response, Photon)

    def create(self, path: str, public_photon: bool = False) -> bool:
        if not os.path.exists(path):
            raise ValueError(f"Photon file not found: {path}")
        with open(path, "rb") as file:
            response = self._post(
                f"/photons/{_get_photon_endpoint(public_photon)}", files={"file": file}
            )
            return response.ok

    def get(
        self, id_or_photon: Union[str, Photon], public_photon: bool = False
    ) -> Photon:
        id_ = id_or_photon if isinstance(id_or_photon, str) else id_or_photon.id_
        response = self._get(f"/photons/{_get_photon_endpoint(public_photon)}/{id_}")
        return self._ws.ensure_type(response, Photon)

    def download(
        self,
        id_or_photon: Union[str, Photon],
        path: Optional[str] = None,
        public_photon: bool = False,
    ):
        id_ = id_or_photon if isinstance(id_or_photon, str) else id_or_photon.id_
        if path is None:
            path = str(CACHE_DIR / f"tmp.{id}.photon")
            need_rename = True
        else:
            need_rename = False

        response = self._get(
            f"/photons/{_get_photon_endpoint(public_photon)}/{id_}/content",
            stream=True,
        )
        if not response.ok:
            raise ValueError(
                f"Failed to download photon {id_}. Details: {response.text}"
            )
        with open(path, "wb") as f:
            f.write(response.content)

        photon = load(path)

        # backward-compatibility: support the old style photon.name and photon.model,
        # and the newly updated photon._photon_name and photon._photon_model
        try:
            photon_name = photon._photon_name
            photon_model = photon._photon_model
        except AttributeError:
            photon_name = photon.name  # type: ignore
            photon_model = photon.model  # type: ignore

        if need_rename:
            new_path = CACHE_DIR / f"{photon_name}.{id}.photon"
            os.rename(path, new_path)
        else:
            new_path = path

        # TODO: use remote creation time
        logger.trace(
            "Adding photon to local cache:"
            f" {id_} {photon_name} {photon_model} {str(new_path)}"
        )
        add_photon(id_, photon_name, photon_model, str(new_path))  # type: ignore

    def delete(
        self, id_or_photon: Union[str, Photon], public_photon: bool = False
    ) -> bool:
        id_ = id_or_photon if isinstance(id_or_photon, str) else id_or_photon.id_
        response = self._delete(f"/photons/{_get_photon_endpoint(public_photon)}/{id_}")
        return self._ws.ensure_ok(response)

    def run(self, spec: LeptonDeployment) -> bool:
        """
        Run a photon with the given deployment spec.
        """
        response = self._post("/deployments", json=self.safe_json(spec))
        return self._ws.ensure_ok(response)

    def list_local(self):
        """
        List the photons in the local cache directory.
        """
        photons = find_all_local_photons()
        return [p[1] for p in photons]

    def delete_local(self, name: str, remove_all: bool = False):
        return remove_local_photon(name, remove_all)
