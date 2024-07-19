"""
Utility functions to interact with the remote server.
"""

import atexit
import gc
import hashlib
import inspect
import re
import time
from typing import Optional, Union, Type
import uuid
import weakref

from loguru import logger

from leptonai.photon import Photon
from leptonai.photon.util import create as create_photon
from leptonai import config
from leptonai.api import v0 as api_v0
from leptonai.api.v0.util import APIError
from leptonai.client import Client, current


_unique_name_pattern = re.compile(r"cldrun-[0-9a-f]{25}")
_unique_photon_id_pattern = re.compile(r"cldrun-[0-9a-f]{25}-[0-9a-z]{8}")


def _make_unique_name() -> str:
    """
    Make a unique name for a photon.
    """
    m = hashlib.md5(uuid.uuid4().bytes)
    return "cldrun-" + m.hexdigest()[7:]


class Remote(object):
    """
    Remote: experimental feature to run a photon remotely.
    """

    # In the Remote class, we wait for at most 10 minutes for the photon to be ready.
    _MAX_WAIT_TIME = 600
    # In the Remote class, we wait for at most 30 seconds for DNS and other
    # propagation between the deployment being ready and the client being accessable.
    _MAX_CLIENT_WAIT_TIME = 30
    # Similar to the default timeout in the deployment class, we will set the default timeout to 1 hour.
    _DEFAULT_TIMEOUT = config.CLOUDRUN_DEFAULT_TIMEOUT
    # In the Remote class, we wait for 1 second between each check for the photon to be ready.
    _DEFAULT_WAIT_INTERVAL = 1

    # A best-effort global variable for Remote objects, and a best-effort cleanup function.
    # This is used to make sure that we do clean things up when the program exits.
    _all_remotes = weakref.WeakSet()

    def __init__(self, photon: Union[Type[Photon], str, Photon], **kwargs):
        """
        Run a photon remotely.

        Args:
            Photon: a photon object, or a string representing a photon.
            **kwargs: Keyword arguments to create the deployment. Currently, they are:
                resource_shape: str = DEFAULT_RESOURCE_SHAPE,
                min_replicas: int = 1,
                mounts: Optional[List[str]] = None,
                env_list: Optional[List[str]] = None,
                secret_list: Optional[List[str]] = None,
                no_traffic_timeout: Optional[int] = None,
            See leptonai.api_v0.deployment.run_remote for details.
        """
        self._all_remotes.add(self)
        self.photon = photon
        self.kwargs = kwargs
        self.display_name = str(photon)
        self.unique_name = _make_unique_name()
        # local path to the created photon
        self.path: Optional[str] = None
        # photon id on the remote server
        self.photon_id: Optional[str] = None
        # deployment id on the remote server
        self.deployment_id: Optional[str] = None
        # remote photon client
        self.client = None

        self.conn = api_v0.workspace.current_connection()
        self._last_error = None

        try:
            self._start_up()
        except Exception as e:
            # close things first, and then raise the error.
            self.close()
            raise e

    def _create_and_push_photon(self):
        """
        Creates and pushes the photon to the remote server.
        """
        # First, create and push the photon
        photon = self.photon
        logger.debug(f"Remote: creating photon {self.unique_name} ({photon})")

        if inspect.isclass(photon) and issubclass(photon, Photon):
            photon_instance: Photon = photon(name=self.unique_name)
        elif isinstance(photon, Photon):
            # if the photon is already a Photon object, then directly save it.
            photon_instance: Photon = photon
            photon_instance._photon_name = self.unique_name
        elif isinstance(photon, str):
            # if the photon is a string, then create a Photon object and save it.
            try:
                created_photon = create_photon(name=self.unique_name, model=photon)
                if not isinstance(created_photon, Photon):
                    raise RuntimeError(
                        "Currently we do not support non-python photons yet."
                    )
                photon_instance: Photon = created_photon
            except Exception as e:
                raise RuntimeError(
                    f"Failed to create photon {self.unique_name} from {photon}"
                ) from e
        else:
            raise TypeError(
                f"Invalid photon type: {type(photon)}. Must be a Photon class, object"
                " or a string."
            )
        self.path = photon_instance.save()

        # Second, push the photon
        logger.debug(f"Remote: pushing photon {self.unique_name}")
        response = api_v0.photon.push(self.conn, self.path)
        if response.status_code in (200, 201):
            # Successfully pushed the photon, or the photon has already existed
            self.photon_id = response.json()["id"]
        else:
            raise RuntimeError(
                f"Failed to push photon {self.unique_name} to the workspace. Response:"
                f" {response} {response.text}"
            )

    def _run_photon(self, resume: bool = False):
        if not self.photon_id:
            raise RuntimeError(
                "You hit a programming error: _run_photon should not be called before"
                "photon is created."
            )
        logger.debug(f"Remote: running photon {self.photon_id}")
        if "no_traffic_timeout" not in self.kwargs:
            self.kwargs["no_traffic_timeout"] = self._DEFAULT_TIMEOUT
        if resume:
            # When creating a photon, a missing min_replicas value means it's 1.
            # When updating the deployment, we will need to explicitly pass in the
            # min_replicas value, otherwise the backend will think we are trying to
            # not change it (aka, keeping as 0)
            if "min_replicas" not in self.kwargs:
                self.kwargs["min_replicas"] = 1
            if not self.deployment_id:
                raise RuntimeError(
                    "You hit a programming error: _run_photon should not be called"
                    " with resume=True before deployment is created."
                )
            response = api_v0.deployment.update_deployment(
                self.conn, name=self.deployment_id, **self.kwargs
            )
            if isinstance(response, APIError):
                raise RuntimeError(
                    f"Failed to resume photon {self.photon_id}. Response:"
                    f" {response.message}"
                )
        else:
            response = api_v0.photon.run_remote(
                self.conn,
                id=self.photon_id,
                deployment_name=self.unique_name,
                **self.kwargs,
            )
            if response.status_code in (200, 201):
                self.deployment_id = self.unique_name
            else:
                raise RuntimeError(
                    f"Failed to run photon {self.photon_id}. Response:"
                    f" {response} {response.text}"
                )
        # Wait till the deployment is ready
        if not self.deployment_id:
            raise RuntimeError(
                "You hit a programming error: _wait should not be called before"
                "deployment is created."
            )
        # wait for the photon to be ready
        logger.debug(f"Remote: waiting for photon {self.photon_id} to be ready")
        logger.debug(
            "Go to https://dashboard.lepton.ai/ to check detailed progress of the"
            f" deployment {self.deployment_id}."
        )
        start = time.time()
        is_deployment_ready = False
        ret = None
        while not is_deployment_ready and time.time() - start < self._MAX_WAIT_TIME:
            ret = api_v0.deployment.get_deployment(self.conn, self.deployment_id)
            if isinstance(ret, APIError):
                raise RuntimeError(
                    f"Failed to get the status of deployment {self.deployment_id}."
                    f" Response: {ret.message}."
                )
            elif ret["status"]["state"] in ("Running", "Ready"):  # noqa
                # In earlier versions of the backend we had "Running" as a state.
                # As a result we will temporarily use both, and in the long run we
                # will use "Ready". ref: https://github.com/leptonai/lepton/pull/3152
                is_deployment_ready = True
                logger.debug(f"Remote: photon {self.deployment_id} is ready")
            else:
                # Test if there are earlier terminations causing the deployment to fail
                ret = api_v0.deployment.get_termination(self.conn, self.deployment_id)
                if not isinstance(ret, APIError) and len(ret):
                    # Earlier termination detected. Raise an error.
                    self._last_error = ret
                    logger.error(
                        f"{self.deployment_id} seems to have failures. One failure is"
                        " shown below:"
                    )
                    print(list(self._last_error.values())[0][0]["message"])  # type: ignore
                    logger.error(
                        "Inspect more details of the failure using the last_error()"
                        " function."
                    )
                    # Note: we will not raise an exception, so that we will have a
                    # chance to inspect the error.
                    return
                time.sleep(self._DEFAULT_WAIT_INTERVAL)
        if not is_deployment_ready:
            raise RuntimeError(
                f"Failed to run photon {self.photon_id} in time. Last state: {ret}"
            )
        # Note: we will double check openapi correctness, as there is a little bit of
        # delay between the deployment is ready and the openapi is ready, because the
        # load balancer in front of the deployment may need a bit of startup time.
        is_client_ready = False
        start = time.time()
        while not is_client_ready and time.time() - start < self._MAX_CLIENT_WAIT_TIME:
            try:
                self.client = Client(current(), self.deployment_id, no_check=True)
                is_client_ready = bool(self.client.openapi)
            except ConnectionError:
                # Temporary solution: Between deployment ready and client ready, sometimes
                # a 503 server not ready is returned. In this case, we will catch the
                # connection error and simply retry.
                continue
            time.sleep(self._DEFAULT_WAIT_INTERVAL)
        if self.client is None or not self.client.openapi:
            self._last_error = (
                f"Failed to get openapi for photon {self.photon_id} in time."
            )
            raise RuntimeError(self._last_error)
        logger.debug(f"Remote: client for {self.deployment_id} is ready")

    def last_error(self):
        return self._last_error

    def _start_up(self) -> None:
        """
        Starts up the remote run.
        """
        self._create_and_push_photon()
        self._run_photon()

    def restart(self) -> None:
        """
        Restarts the current run if it has been closed.
        """
        # Note: there is one caveat in the current implementation, in the sense
        # that, if someone runs a clean() operation between the launch of this
        # Remote object and the restart, then the underlying photon will have
        # been removed, and we will have to recreate the photon. Right now,
        # we will not handle this case, and we will simply raise an error.
        if self.healthz():
            # If the service is still up - don't do anything, just return.
            return
        try:
            if not self.deployment_id:
                # Never started up before, start up.
                self._start_up()
            else:
                # Resume by re-running the photon
                self._run_photon(resume=True)
        except Exception as e:
            # close things first, and then raise the error.
            self.close()
            raise e

    def close(self):
        """
        Closes the current run.
        """
        logger.debug(f"Remote: closing remote {self.unique_name}({self.display_name})")
        # Implementation note: we will not raise any error if the close() operation
        # fails, as we want to make sure that the close() operation is best-effort.
        self.client = None
        if self.deployment_id is not None:
            logger.debug(f"Remote: removing deployment {self.deployment_id}")
            api_v0.deployment.remove_deployment(self.conn, self.deployment_id)
            self.deployment_id = None
        if self.photon_id is not None:
            logger.debug(f"Remote: removing photon {self.photon_id}")
            api_v0.photon.remove_remote(self.conn, self.photon_id)
            self.photon_id = None
        if self.path is not None:
            logger.debug(f"Remote: removing local photon {self.path}")
            api_v0.photon.remove_local(self.path)
            self.path = None

    @classmethod
    def _atexit_cleanup(cls):
        """
        A best-effort cleanup function for the remote objects.

        You should not call this function directly. It is invoked by atexit.
        """
        # For any remote items that are explicitly `del`ed but not garbage collected,
        # we do a garbage collection here.
        gc.collect()
        # If there are remaining remote items (i.e. created inside __main__ or the
        # interpreter), we will try to close them explicitly.
        for remote in cls._all_remotes:
            remote.close()

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
            # TODO: wrap the client function in a retry function, so that if the
            # client call receives an HTTP 503 error, we automatically try to
            # restart the photon and retry the call.
            return self.client.__getattr__(name)
        except AttributeError:
            raise AttributeError(f"Cannot find attribute {name}.")

    def __dir__(self):
        own_dir = ["close", "client", "healthz", "restart", "close"]
        if self.client is None:
            return own_dir
        else:
            return own_dir + list(self.client.__dir__())


atexit.register(Remote._atexit_cleanup)


def clean_deployments(force_remove: bool = False):
    """
    A utility function to clean the deployments created by cloudrun in the current workspace.
    """
    conn = api_v0.workspace.current_connection()
    deployments = api_v0.deployment.list_deployment(conn)
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
                    api_v0.deployment.remove_deployment(conn, deployment["name"])


def clean_photons():
    """
    A utility function to clean the photons created by cloudrun in the current workspace.
    """
    conn = api_v0.workspace.current_connection()
    photons = api_v0.photon.list_remote(conn)
    if isinstance(photons, APIError):
        raise RuntimeError("Failed to list photons.")
    else:
        for photon in photons:
            if _unique_photon_id_pattern.match(photon["id"]):
                logger.debug(f"Removing {photon['id']}")
                api_v0.photon.remove_remote(conn, photon["id"])


def clean_local_photons():
    """
    A utility function to clean the photons created by
    """
    photons = api_v0.photon.list_local()
    for p in photons:
        if _unique_name_pattern.match(p):
            logger.debug(f"Removing {p}")
        api_v0.photon.remove_local(p, remove_all=True)


def clean(force_remove: bool = False):
    """
    A utility function to clean the deployments and photons created by cloudrun in the current workspace.
    """
    clean_deployments(force_remove)
    clean_photons()
    clean_local_photons()
