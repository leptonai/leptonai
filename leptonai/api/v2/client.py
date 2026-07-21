"""
The api/v1/client module serves as the single entry point of all apis, holding
information such as the url auth token, as well as caching runtime objects
such as http sessions.
"""

import os
import time
import re
import threading
import requests
from typing import Optional, Union, Dict, Tuple

from .log import LogAPI

from .types.workspace import WorkspaceInfo

# import the related API resources. Note that in all these files, they should
# not import workspace to avoid circular imports.
from .api_resource import APIResourse
from .dedicated_node_groups import DedicatedNodeGroupAPI
from .deployment import DeploymentAPI
from .endpoint import EndpointAPI
from .devpod import DevPodAPI
from .job import JobAPI
from .secret import SecretAPI
from .pod import PodAPI
from .ingress import IngressAPI
from .storage import StorageAPI
from .resource_shape import ResourceShapeAPI
from .template import TemplateAPI
from .finetune import FineTuneAPI
from .raycluster import RayClusterAPI


from .utils import (
    WorkspaceForbiddenError,
    _get_full_workspace_api_url,
    WorkspaceUnauthorizedError,
    WorkspaceNotFoundError,
    _get_workspace_origin_url,
    WorkspaceConfigurationError,
)
from .workspace_record import WorkspaceRecord
from loguru import logger


# Token expiry warning: warn at most once per process
HAS_WARNED_TOKEN_EXPIRE: bool = False


# Process-wide memo of the resolved new-deployment-API flag, keyed by workspace
# URL. A single `lep` invocation targets exactly one workspace, but it may build
# several short-lived `APIClient` instances (e.g. the parallel `lep log get`
# workers each construct their own). Keying the resolved flag on the workspace
# URL commits one dispatch decision for the whole invocation, so no two clients —
# and no two reads on one client — can disagree and split a logical operation
# across the legacy /deployments and the new /endpoints|/devpods APIs.
_NEW_DEPLOYMENT_API_FLAG_CACHE: Dict[str, bool] = {}

# Guards the check-resolve-commit sequence in `new_deployment_api_enabled`. The
# GIL makes each individual dict op atomic, but not the read-then-/workspace-
# resolve-then-write span: without this lock, two threads that hit a cold memo
# concurrently (e.g. `lep log get` workers, each with its own APIClient) could
# each issue their own /workspace call, get different transient outcomes, and
# route their in-flight requests to different API families before last-write-wins
# settles the memo. Single-flight under this lock guarantees exactly one
# resolution per workspace URL and one committed dispatch decision.
_FLAG_CACHE_LOCK = threading.Lock()

# Bounded retry for the one-time flag resolution. The CLI is a short-lived
# process: a couple of quick retries smooth over a transient /workspace blip
# without a per-command round-trip, and the committed outcome (including a
# committed False after retries are exhausted) then holds for the process.
_FLAG_RESOLVE_RETRIES: int = 2
_FLAG_RESOLVE_BACKOFF_SECONDS: float = 0.25


def reset_new_deployment_api_flag_cache(url: Optional[str] = None) -> None:
    """Drop the memoized new-deployment-API dispatch flag.

    The flag is resolved once and committed for the lifetime of the process (see
    :attr:`APIClient.new_deployment_api_enabled`). That is correct for the
    short-lived ``lep`` CLI, but a long-lived SDK consumer (a notebook or a
    service that ``import leptonai`` and stays up) would otherwise never observe
    an ``enable_new_deployment_api`` flip on the workspace — the api-server does
    permit toggling it. Call this to force the next dispatch to re-resolve.

    :param url: clear only the entry for this workspace URL; ``None`` clears all.
    """
    with _FLAG_CACHE_LOCK:
        if url is None:
            _NEW_DEPLOYMENT_API_FLAG_CACHE.clear()
        else:
            _NEW_DEPLOYMENT_API_FLAG_CACHE.pop(url, None)


class APIClient(object):
    """
    A Lepton API client that is associated with a workspace. This class holds all
    the apis callable by the user.
    """

    def __init__(
        self,
        workspace_id: Optional[str] = None,
        auth_token: Optional[str] = None,
        url: Optional[str] = None,
        workspace_origin_url: Optional[str] = None,
    ):
        """
        Creates a workspace api client by identifying the workspace in the following
        order:
        - If workspace_id is given, log in to the given workspace. Workspace id could
        also include the token as a complete credential string, which you can obtain
        from https://dashboard.dgxc-lepton.nvidia.com/credentials.
        - If workspace_id is not given, but there is LEPTON_WORKSPACE_ID in the environment,
        log into that workspace. We will look for LEPTON_WORKSPACE_TOKEN as the auth token,
        and LEPTON_WORKSPACE_URL as the workspace url, if they exist.
        - If we have depleted all the options and still cannot determine a workspace
        id, we will throw an error.

        This function is intended to be used inside lepton deployments to log in to the
        workspace programmatically.
        """
        # We will resolve workspace id in the following order:
        #  - user specified one
        #  - environment variable LEPTON_WORKSPACE_ID
        #  - current workspace of the workspace record
        # and if there is still no choice, we will throw an error.
        workspace_id = (
            workspace_id
            or os.environ.get("LEPTON_WORKSPACE_ID")
            or (WorkspaceRecord.current().id_ if WorkspaceRecord.current() else None)
        )
        if workspace_id is None:
            raise WorkspaceConfigurationError(
                "You must specify workspace_id or set LEPTON_WORKSPACE_ID in the"
                " environment, or use commandline `lep login` to log in to a "
                " workspace. If you do not know your workspace credentials, go to"
                " https://dashboard.dgxc-lepton.nvidia.com/credentials and login with"
                " the credential string."
            )
        # If workspace_id contains colon, it is a credential that also contains the token.
        if ":" in workspace_id and not auth_token:
            workspace_id, auth_token = workspace_id.split(":", 1)
        # We will then resolve the auth token in the following order:
        # - user specified one
        # - environment variable LEPTON_WORKSPACE_TOKEN
        # - auth token of the workspace record
        auth_token = (
            auth_token
            or os.environ.get("LEPTON_WORKSPACE_TOKEN")
            or (
                WorkspaceRecord.get(workspace_id).auth_token  # type: ignore
                if WorkspaceRecord.has(workspace_id)
                else None
            )
        )
        # We will then resolve the url in a similar order.
        url = (
            url
            or os.environ.get("LEPTON_WORKSPACE_URL")
            or (
                WorkspaceRecord.get(workspace_id).url  # type: ignore
                if WorkspaceRecord.has(workspace_id)
                else None
            )
            or _get_full_workspace_api_url(workspace_id)
        )
        workspace_origin_url = (
            workspace_origin_url
            or os.environ.get("LEPTON_WORKSPACE_ORIGIN_URL")
            or (
                WorkspaceRecord.get(workspace_id).workspace_origin_url
                if WorkspaceRecord.has(workspace_id)
                else None
            )
            or _get_workspace_origin_url(url)
        )

        token_expires_at = (
            getattr(WorkspaceRecord.get(workspace_id), "token_expires_at", None)
            if WorkspaceRecord.has(workspace_id)
            else None
        )

        self.workspace_id: str = workspace_id
        self.auth_token: Optional[str] = auth_token
        self.url: str = url
        self.workspace_origin_url: Optional[str] = workspace_origin_url
        self.token_expires_at: Optional[int] = token_expires_at

        if self.token_expires_at is not None:
            global HAS_WARNED_TOKEN_EXPIRE
            if not HAS_WARNED_TOKEN_EXPIRE:
                now_ms = int(time.time() * 1000)
                if now_ms >= self.token_expires_at:
                    logger.warning(
                        "Workspace token has expired. Please issue a new token and run"
                        " `lep workspace login` again."
                    )
                    HAS_WARNED_TOKEN_EXPIRE = True
                else:
                    ms_left = self.token_expires_at - now_ms
                    days_left = (ms_left + 86_400_000 - 1) // 86_400_000  # ceil to days
                    if days_left < 10:
                        logger.warning(
                            f"Workspace token will expire in {days_left} day(s). Please"
                            " re-issue a new token and run `lep workspace login` again."
                        )
                        HAS_WARNED_TOKEN_EXPIRE = True

        # Creates a connection for us to use.
        self._header = {}
        if self.auth_token:
            self._header["Authorization"] = "Bearer " + self.auth_token

        if self.workspace_origin_url:
            # print(f"workspace_origin_url: {workspace_origin_url}")
            self._header["origin"] = workspace_origin_url

        logger.trace(
            "Current workspace info:\n"
            f"  id: {self.workspace_id}\n"
            f"  url: {self.url}\n"
            f"  auth_token: {self.auth_token[:2]}****{self.auth_token[-2:]}\n"
            f"  workspace_origin_url: {self.workspace_origin_url}"
        )

        # In default, timeout for the API calls is set to 120 seconds.
        self._timeout = 120
        self._session = requests.Session()
        if os.environ.get("LEPTON_DEBUG_HEADERS"):
            # LEPTON_DEBUG_HEADERS should be in the format of comma separated
            # header_key=header_value pairs.
            try:
                header_pairs = os.environ["LEPTON_DEBUG_HEADERS"].split(",")
                for pair in header_pairs:
                    key, value = pair.split("=")
                    self._header.setdefault(key, value)
            except ValueError:
                raise RuntimeError(
                    "LEPTON_DEBUG_HEADERS should be in the format of comma separated"
                    " header_key=header_value pairs. Got"
                    f" {os.environ['LEPTON_DEBUG_HEADERS']}"
                )

        # Add individual APIs
        self.nodegroup = DedicatedNodeGroupAPI(self)
        self.job = JobAPI(self)
        self.secret = SecretAPI(self)
        self.ingress = IngressAPI(self)
        self.storage = StorageAPI(self)
        self.log = LogAPI(self)
        self.template = TemplateAPI(self)
        self.finetune = FineTuneAPI(self)
        self.shapes = ResourceShapeAPI(self)
        self.raycluster = RayClusterAPI(self)

        # Deployment ("endpoint") and pod ("devpod") each have two backing
        # implementations: the legacy /deployments-based API and the new
        # /endpoints|/devpods-based API. The public `deployment` and `pod`
        # attributes are @property accessors below that dispatch to one of these
        # based on the cached `enable_new_deployment_api` workspace flag. Legacy
        # is the default and the fail-safe. Internal code that must always reach
        # the legacy /deployments routes (e.g. LogAPI) can use these directly.
        self._deployment_legacy = DeploymentAPI(self)
        self._pod_legacy = PodAPI(self)
        self._endpoint_api = EndpointAPI(self)
        self._devpod_api = DevPodAPI(self)

        # Per-instance mirror of the process-wide resolved flag (keyed by
        # workspace URL in `_NEW_DEPLOYMENT_API_FLAG_CACHE`). None means "not yet
        # read on this client"; it is populated from the memo on first access.
        self._new_deployment_api_enabled: Optional[bool] = None

    @property
    def new_deployment_api_enabled(self) -> bool:
        """Whether the workspace has the new endpoint/devpod API enabled.

        Resolved once, then committed for the lifetime of the *process* (not
        just this client) via a workspace-URL-keyed memo. The first access on
        the first client for a workspace does a single ``info()`` resolution
        with a small bounded retry; the resulting bool — ``True`` OR ``False``,
        including a ``False`` committed after the retries are exhausted — is
        stored and returned unconditionally for every later access, on this
        client and on any other client built for the same workspace in the same
        invocation. The semantics mirror the dashboard's ``useEndpointApiMode``:
        only an explicit ``true`` for ``features.enable_new_deployment_api``
        switches to the new routes; an absent field, ``false``, or a missing
        ``features`` object stays on the legacy routes.

        Why commit unconditionally (superseding the earlier no-cache-on-failure
        design): the ``lep`` CLI is a short-lived process, and many operations
        span several dispatch reads (a preflight list then a create, an update's
        get-then-patch-then-verify, a pod list then its per-replica IP lookup)
        or several clients (the parallel ``lep log get`` workers). If a
        *transient* /workspace failure yielded legacy for one read and a later
        read recovered the real flag, the operation would split across the
        legacy /deployments and the new /endpoints|/devpods APIs — the exact
        multi-call inconsistency class fixed here. Intra-process consistency
        therefore beats freshness. The earlier concern that fail-to-legacy could
        silently land an endpoint-flavored create on /deployments in a flag-on
        workspace is now backstopped SERVER-SIDE (api-server MR !7865 rejects
        such a create with 400), so committing legacy after a genuine, retried
        resolution failure fails loud rather than silently wrong.

        SDK implication: because the commit lasts the whole process, a long-lived
        consumer (a notebook or service that keeps ``leptonai`` imported) will
        NOT observe a workspace's ``enable_new_deployment_api`` being toggled
        after the first dispatch — the api-server permits the toggle, but this
        client will keep routing to the family it first resolved. That is
        intentional (freshness is traded for per-operation consistency); a
        consumer that needs to pick up a flip can call
        :func:`reset_new_deployment_api_flag_cache` to force a re-resolution.

        Concurrency: the cold-memo resolve-and-commit runs single-flight under
        ``_FLAG_CACHE_LOCK`` (double-checked), so concurrent first accesses from
        different threads/clients on the same workspace URL do exactly one
        /workspace resolution and commit one dispatch decision — they cannot
        split routing across API families.

        @implements LEP-5664, LEP-5665 (flag detection)
        """
        cached = _NEW_DEPLOYMENT_API_FLAG_CACHE.get(self.url)
        if cached is not None:
            self._new_deployment_api_enabled = cached
            return cached
        with _FLAG_CACHE_LOCK:
            # Re-check under the lock: another thread may have resolved and
            # committed while we waited, in which case we adopt its decision
            # rather than issuing a second /workspace call.
            cached = _NEW_DEPLOYMENT_API_FLAG_CACHE.get(self.url)
            if cached is not None:
                self._new_deployment_api_enabled = cached
                return cached
            resolved = self._resolve_new_deployment_api()
            _NEW_DEPLOYMENT_API_FLAG_CACHE[self.url] = resolved
            self._new_deployment_api_enabled = resolved
            return resolved

    def _resolve_new_deployment_api(self) -> bool:
        """Resolve the new-deployment-API flag from workspace info, once.

        Always returns a definite bool: an explicit ``features
        .enable_new_deployment_api is True`` yields ``True``; an absent flag,
        missing ``features``, or an unresolvable /workspace call (after a small
        bounded retry) all yield ``False``. This is called at most once per
        workspace URL per process — the caller commits the result to the
        process-wide memo — so a transient blip is retried here rather than
        being re-litigated on every subsequent dispatch read.
        """
        info = None
        for attempt in range(_FLAG_RESOLVE_RETRIES + 1):
            try:
                info = self.info()
                break
            except Exception as e:
                if attempt < _FLAG_RESOLVE_RETRIES:
                    logger.trace(
                        "Could not resolve new deployment API flag (attempt"
                        f" {attempt + 1}), retrying: {e}"
                    )
                    time.sleep(_FLAG_RESOLVE_BACKOFF_SECONDS * (2**attempt))
                else:
                    logger.trace(
                        "Could not resolve new deployment API flag after"
                        f" {_FLAG_RESOLVE_RETRIES + 1} attempts, committing"
                        f" legacy: {e}"
                    )
                    return False
        features = getattr(info, "features", None)
        if features is None:
            return False
        return features.enable_new_deployment_api is True

    @property
    def deployment(self) -> Union[DeploymentAPI, "EndpointAPI"]:
        """The deployment (endpoint) API.

        Dispatches to the new /endpoints-based :class:`EndpointAPI` when the
        workspace flag is on, otherwise the legacy /deployments-based
        :class:`DeploymentAPI`. Both expose the same method surface and return
        :class:`LeptonDeployment`-shaped objects, so callers are unaffected.
        """
        if self.new_deployment_api_enabled:
            return self._endpoint_api
        return self._deployment_legacy

    @property
    def pod(self) -> Union[PodAPI, "DevPodAPI"]:
        """The pod (devpod) API.

        Dispatches to the new /devpods-based :class:`DevPodAPI` when the
        workspace flag is on, otherwise the legacy /deployments-based
        :class:`PodAPI`.
        """
        if self.new_deployment_api_enabled:
            return self._devpod_api
        return self._pod_legacy

    def _safe_add(self, kwargs: Dict) -> Dict:
        """
        Internal utility function to add default values to the kwargs.
        """
        kwargs.setdefault("headers", self._header)
        kwargs.setdefault("timeout", self._timeout)
        # if kwargs does have headers, but does not have Authorization, we will add it.
        for k, v in self._header.items():
            kwargs["headers"].setdefault(k, v)
        return kwargs

    def _get(self, path: str, *args, **kwargs):
        return self._session.get(self.url + path, *args, **self._safe_add(kwargs))

    def _post(self, path: str, *args, **kwargs):
        return self._session.post(self.url + path, *args, **self._safe_add(kwargs))

    def _patch(self, path: str, *args, **kwargs):
        return self._session.patch(self.url + path, *args, **self._safe_add(kwargs))

    def _put(self, path: str, *args, **kwargs):
        return self._session.put(self.url + path, *args, **self._safe_add(kwargs))

    def _delete(self, path: str, *args, **kwargs):
        return self._session.delete(self.url + path, *args, **self._safe_add(kwargs))

    def _head(self, path: str, *args, **kwargs):
        return self._session.head(self.url + path, *args, **self._safe_add(kwargs))

    def info(self) -> WorkspaceInfo:
        """
        Returns the workspace info.
        """
        ws_api = APIResourse(self)
        response = self._get("/workspace")
        auth_token_hint = (
            self.auth_token[:2] + "****" + self.auth_token[-2:]
            if self.auth_token
            else ""
        )

        if response.status_code == 401:
            raise WorkspaceUnauthorizedError(
                workspace_id=self.workspace_id,
                workspace_url=self.url,
                auth_token=auth_token_hint,
            )

        if response.status_code == 404:
            raise WorkspaceNotFoundError(
                workspace_id=self.workspace_id,
                workspace_url=self.url,
                auth_token=auth_token_hint,
            )

        if response.status_code == 403:
            raise WorkspaceForbiddenError(
                workspace_id=self.workspace_id,
                workspace_url=self.url,
                auth_token=auth_token_hint,
            )

        return ws_api.ensure_type(response, WorkspaceInfo)

    def version(self, info=None) -> Optional[Tuple[int, int, int]]:
        """
        Returns a tuple of (major, minor, patch) of the workspace version, or if
        this is a dev workspace, returns None.
        """
        info = info if info else self.info()
        _semver_pattern = re.compile(
            r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"  # noqa: E501
            # noqa: W605
        )

        match = _semver_pattern.match(info.git_commit)
        return (
            (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            if match
            else None
        )

    def token(self) -> Union[str, None]:
        """
        Returns the current workspace token.
        """
        return self.auth_token

    def get_workspace_id(self) -> Union[str, None]:
        return self.workspace_id

    def get_workspace_name(self) -> Union[str, None]:
        return WorkspaceRecord.current().display_name

    def get_dashboard_base_url(self) -> Optional[str]:
        """
        Returns the base dashboard URL derived from the current workspace URL.
        """
        base = (self.url or "").replace("://gateway", "://dashboard", 1)
        base = base.replace("/api/v2", "", 1)
        base = base.replace("/workspaces", "/workspace", 1)
        return base
