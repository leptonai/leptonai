import os
from typing import List, Union, Optional

from loguru import logger

from leptonai.config import CACHE_DIR, LEPTON_RESERVED_ENV_NAMES
from leptonai.photon.util import load
from leptonai.photon.base import (
    add_photon,
    remove_local_photon,
    find_all_local_photons,
)

from .api_resource import APIResourse
from .types.deployment import Mount, EnvVar, EnvValue
from .types.photon import Photon as Photon
from .types.deployment import LeptonDeployment


def make_mounts_from_strings(
    mounts: Optional[List[str]],
) -> Optional[List[Mount]]:
    """
    Parses a list of mount strings into a list of Mount objects.
    """
    if not mounts:
        return None
    mount_list = []
    for mount_str in mounts:
        parts = mount_str.split(":")
        if len(parts) == 2:
            # TODO: sanity check if the mount path exists.
            mount_list.append(Mount(path=parts[0].strip(), mount_path=parts[1].strip()))  # type: ignore
        else:
            raise ValueError(f"Invalid mount definition: {mount_str}")
    return mount_list


def make_env_vars_from_strings(
    env: Optional[List[str]], secret: Optional[List[str]]
) -> Optional[List[EnvVar]]:
    if not env and not secret:
        return None
    env_list = []
    for s in env if env else []:
        try:
            k, v = s.split("=", 1)
        except ValueError:
            raise ValueError(f"Invalid environment definition: [red]{s}[/]")
        if k in LEPTON_RESERVED_ENV_NAMES:
            raise ValueError(
                "You have used a reserved environment variable name that is "
                "used by Lepton internally: {k}. Please use a different name. "
                "Here is a list of all reserved environment variable names:\n"
                f"{LEPTON_RESERVED_ENV_NAMES}"
            )
        env_list.append(EnvVar(name=k, value=v))
    for s in secret if secret else []:
        # We provide the user a shorcut: instead of having to specify
        # SECRET_NAME=SECRET_NAME, they can just specify SECRET_NAME
        # if the local env name and the secret name are the same.
        k, v = s.split("=", 1) if "=" in s else (s, s)
        if k in LEPTON_RESERVED_ENV_NAMES:
            raise ValueError(
                "You have used a reserved secret name that is "
                "used by Lepton internally: {k}. Please use a different name. "
                "Here is a list of all reserved environment variable names:\n"
                f"{LEPTON_RESERVED_ENV_NAMES}"
            )
        # TODO: sanity check if these secrets exist.
        env_list.append(EnvVar(name=k, value_from=EnvValue(secret_name_ref=v)))
    return env_list


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
        return self.ensure_list(response, Photon)

    def create(self, path: str, public_photon: bool = False) -> Photon:
        if not os.path.exists(path):
            raise ValueError(f"Photon file not found: {path}")
        with open(path, "rb") as file:
            response = self._post(
                f"/photons/{_get_photon_endpoint(public_photon)}", files={"file": file}
            )
            return self.ensure_type(response, Photon)

    def get(
        self, id_or_photon: Union[str, Photon], public_photon: bool = False
    ) -> Photon:
        id_ = id_or_photon if isinstance(id_or_photon, str) else id_or_photon.id_
        response = self._get(f"/photons/{_get_photon_endpoint(public_photon)}/{id_}")
        return self.ensure_type(response, Photon)

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
        return self.ensure_ok(response)

    def run(self, spec: LeptonDeployment) -> bool:
        """
        Run a photon with the given deployment spec.
        """
        response = self._post("/deployments", json=self.safe_json(spec))
        return self.ensure_ok(response)

    def list_local(self):
        """
        List the photons in the local cache directory.
        """
        photons = find_all_local_photons()
        return [p[1] for p in photons]

    def delete_local(self, name: str, remove_all: bool = False):
        return remove_local_photon(name, remove_all)

    def fetch(self, id: str, path: str, public_photon: bool = False):
        """
        Fetch a photon from a workspace.
        :param str id: id of the photon to fetch
        :param str path: path to save the photon to
        """
        if path is None:
            path = str(CACHE_DIR / f"tmp.{id}.photon")
            need_rename = True
        else:
            need_rename = False

        response = self._get(
            f"/photons/{_get_photon_endpoint(public_photon)}/" + id + "?content=true",
            stream=True,
        )

        self.ensure_ok(response)

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
            f" {id} {photon_name} {photon_model} {str(new_path)}"
        )
        add_photon(id, photon_name, photon_model, str(new_path))

        return photon
