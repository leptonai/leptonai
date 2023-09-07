"""
Utility functions to interact with the remote server.
"""
from collections import defaultdict
import hashlib
import inspect
import re
import time
from typing import Optional, Union, Type
import uuid

from loguru import logger

from leptonai.photon import Photon
from leptonai import api
from leptonai.api import APIError
from leptonai.client import Client, current


_unique_process_uuid_value = None
_unique_name_pattern = re.compile(r"cldrun-[0-9a-f]{25}")
_unique_photon_id_pattern = re.compile(r"cldrun-[0-9a-f]{25}-[0-9a-z]{8}")
_refcount = defaultdict(int)


def _unique_process_uuid() -> str:
    """
    Generate a unique uuid for the current process.
    """
    global _unique_process_uuid_value
    if _unique_process_uuid_value is None:
        _unique_process_uuid_value = str(uuid.uuid4())
    return _unique_process_uuid_value


def _make_unique_name(content: str) -> str:
    """
    Make a unique name for a photon.
    """
    m = hashlib.md5(content.encode())
    m.update(_unique_process_uuid().encode())
    return "cldrun-" + m.hexdigest()[7:]


class Remote(object):
    """
    Remote: experimental feature to run a photon remotely.
    """

    _MAX_WAIT_TIME = 600  # In the Remote class, we wait for at most 10 minutes for the photon to be ready.
    _DEFAULT_TIMEOUT = 600  # In the Remote class, we set the timeout for the deployments to be 10 minutes by default.
    _DEFAULT_WAIT_INTERVAL = 1  # In the Remote class, we wait for 1 second between each check for the photon to be ready.

    def __init__(self, photon: Union[Type[Photon], str, Photon], **kwargs):
        """
        Run a photon remotely.

        Args:
            Photon: a photon object, or a string representing a photon.
            **kwargs: Keyword arguments to pass to the photon constructor.
        """
        self.photon = photon
        self.kwargs = kwargs
        self.display_name = ""
        # local path to the created photon
        self.path: Optional[str] = None
        # photon id on the remote server
        self.photon_id: Optional[str] = None
        # deployment id on the remote server
        self.deployment_id: Optional[str] = None
        # remote photon client
        self.client = None
        self.start_up()

    def start_up(self):
        """
        Starts up the remote run.
        """
        # First, create and push the photon
        photon = self.photon
        logger.debug(f"Remote: creating photon {photon}")
        if inspect.isclass(photon) and issubclass(photon, Photon):
            self.display_name = str(photon)
            unique_name = _make_unique_name(str(photon))
            photon_instance: Photon = photon(name=unique_name)
        elif isinstance(photon, Photon):
            # if the photon is already a Photon object, then directly save it.
            unique_name = _make_unique_name(str(photon))
            photon_instance: Photon = photon
            photon_instance.name = unique_name
            self.display_name = str(photon)
        elif isinstance(photon, str):
            # if the photon is a string, then create a Photon object and save it.
            self.display_name = photon
            unique_name = _make_unique_name(photon)
            try:
                created_photon = api.photon.create(name=unique_name, model=photon)
                if not isinstance(created_photon, Photon):
                    raise RuntimeError(
                        "Currently we do not support non-python photons yet."
                    )
                photon_instance: Photon = created_photon
            except Exception as e:
                raise RuntimeError(
                    f"Failed to create photon {unique_name} from {photon}"
                ) from e
        else:
            raise TypeError(
                f"Invalid photon type: {type(photon)}. Must be a Photon class, object"
                " or a string."
            )
        self.path = photon_instance.save()

        # Second, push the photon
        logger.debug(f"Remote: pushing photon {unique_name}")
        conn = api.workspace.current_connection()
        response = api.photon.push(conn, self.path)
        if response.status_code in (200, 201):
            # Successfully pushed the photon, or the photon has already existed
            self.photon_id = response.json()["id"]
        elif response.status_code == 409:
            pattern = r'photons\.lepton\.ai "(.*?)" already exists'
            match = re.search(pattern, response.json()["message"])
            if match:
                self.photon_id = match.group(1)
            else:
                raise RuntimeError(
                    "You encountered a programming error: the returned 409 message"
                    " does not have the expected format. Response:"
                    f" {response} {response.text}"
                )
            logger.debug(f"Remote: photon {self.photon_id} already exists, reusing.")
        else:
            raise RuntimeError(
                f"Failed to push photon {unique_name} to the workspace. Response:"
                f" {response} {response.text}"
            )

        # Third, run the photon
        logger.debug(f"Remote: running photon {self.photon_id}")
        if "timeout" not in self.kwargs:
            self.kwargs["no_traffic_timeout"] = self._DEFAULT_TIMEOUT
        response = api.photon.run_remote(
            conn, id=self.photon_id, deployment_name=unique_name, **self.kwargs
        )
        if response.status_code == 201:
            self.deployment_id = unique_name
        elif response.status_code == 409:
            pattern = "deployment (.*?) already exists"
            match = re.search(pattern, response.json()["message"])
            if match:
                self.deployment_id = match.group(1)
            else:
                raise RuntimeError(
                    "You encountered a programming error: the returned 409 message"
                    " does not have the expected format. Response:"
                    f" {response} {response.text}"
                )
            logger.debug(
                f"Remote: deployment {self.deployment_id} already exists, reusing."
            )
        else:
            raise RuntimeError(
                f"Failed to run photon {self.photon_id}. Response:"
                f" {response} {response.text}"
            )

        # wait for the photon to be ready
        logger.debug(f"Remote: waiting for photon {self.photon_id} to be ready")
        start = time.time()
        is_deployment_ready = False
        while not is_deployment_ready and time.time() - start < self._MAX_WAIT_TIME:
            ret = api.deployment.get_deployment(conn, self.deployment_id)
            if isinstance(ret, APIError):
                raise RuntimeError(
                    f"Failed to get the status of deployment {self.deployment_id}."
                    f" Response: {ret.message}."
                )
            elif ret["status"]["state"] == "Running":  # noqa
                is_deployment_ready = True
            else:
                # Test if there are earlier terminations causing the deployment to fail
                ret = api.deployment.get_termination(conn, self.deployment_id)
                if not isinstance(ret, APIError) and len(ret):
                    # Earlier termination detected. Raise an error.
                    raise RuntimeError(
                        f"{self.deployment_id} seems to have failures. Inspect the"
                        f" failure using `lep deployment log -n {self.deployment_id}`."
                    )
                time.sleep(self._DEFAULT_WAIT_INTERVAL)
        if not is_deployment_ready:
            raise RuntimeError(
                f"Failed to run photon {self.photon_id} in time. Last state: {ret}"
            )

        # Note: we will double check openapi correctness, as there is a little bit of
        # delay between the deployment is ready and the openapi is ready, because the
        # load balancer in front of the deployment may need a bit of startup time.
        self.client = Client(current(), self.deployment_id)
        while not self.client.openapi and time.time() - start < self._MAX_WAIT_TIME:
            # logger.debug("Remote: cannot get openapi, recreating client...")
            time.sleep(self._DEFAULT_WAIT_INTERVAL)
            self.client = Client(current(), self.deployment_id)
        if not self.client.openapi:
            raise RuntimeError(
                f"Failed to get openapi for photon {self.photon_id} in time."
            )

        global _refcount
        _refcount[self.deployment_id] += 1
        logger.debug(f"Remote: photon {self.deployment_id} is ready")

    def alive(self) -> bool:
        """
        Returns True if the function is alive, False otherwise.
        """
        if self.client is None:
            return False
        else:
            return self.client.healthz()

    def close(self):
        """
        Closes the current run.
        """
        self.client = None
        global _refcount
        _refcount[self.deployment_id] -= 1
        if _refcount[self.deployment_id] == 0:
            # Only when we get to refcount=0 do we remove the deployment and photons.
            conn = api.workspace.current_connection()
            if self.deployment_id is not None:
                logger.debug(f"Remote: removing deployment {self.deployment_id}")
                api.deployment.remove_deployment(conn, self.deployment_id)
                self.deployment_id = None
            if self.photon_id is not None:
                logger.debug(f"Remote: removing photon {self.photon_id}")
                api.photon.remove_remote(conn, self.photon_id)
                self.photon_id = None
            if self.path is not None:
                logger.debug(f"Remote: removing local photon {self.path}")
                api.photon.remove_local(self.path)
                self.path = None

    def __str__(self):
        return f"Remote({self.display_name}, deployment_id={self.deployment_id})"

    def __del__(self):
        self.close()

    def healthz(self) -> bool:
        return self.client is not None and self.client.healthz()

    def __getattr__(self, name):
        if self.client is None:
            raise AttributeError(
                f"Cannot find attribute {name}, and the client is not set up yet."
            )
        try:
            return self.client.__getattr__(name)
        except AttributeError:
            raise AttributeError(f"Cannot find attribute {name}.")

    def __dir__(self):
        own_dir = ["close", "client"]
        if self.client is None:
            return own_dir
        else:
            return own_dir + list(self.client.__dir__())


def clean_deployments(force_remove: bool = False):
    """
    A utility function to clean the deployments created by cloudrun in the current workspace.
    """
    conn = api.workspace.current_connection()
    deployments = api.deployment.list_deployment(conn)
    if isinstance(deployments, APIError):
        raise RuntimeError("Failed to list deployments.")
    else:
        for deployment in deployments:
            if _unique_name_pattern.match(deployment["name"]):
                # Do not delete currently running deployments unless we force a removal
                if force_remove or (
                    deployment["status"]["state"] == "Not Ready"
                    and deployment["resource_requirement"]["min_replicas"] == 0
                ):
                    # TODO: check if the deployments are being successfully deleted
                    api.deployment.remove_deployment(conn, deployment["name"])


def clean_photons():
    """
    A utility function to clean the photons created by cloudrun in the current workspace.
    """
    conn = api.workspace.current_connection()
    photons = api.photon.list_remote(conn)
    if isinstance(photons, APIError):
        raise RuntimeError("Failed to list photons.")
    else:
        for photon in photons:
            if _unique_photon_id_pattern.match(photon["id"]):
                logger.debug(f"Removing {photon['id']}")
                api.photon.remove_remote(conn, photon["id"])


def clean_local_photons():
    """
    A utility function to clean the photons created by
    """
    photons = api.photon.list_local()
    for p in photons:
        if _unique_name_pattern.match(p):
            logger.debug(f"Removing {p}")
        api.photon.remove_local(p, remove_all=True)


def clean(force_remove: bool = False):
    """
    A utility function to clean the deployments and photons created by cloudrun in the current workspace.
    """
    clean_deployments(force_remove)
    clean_photons()
    clean_local_photons()
