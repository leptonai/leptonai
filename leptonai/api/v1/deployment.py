import warnings
from typing import Union, List, Iterator, Optional

from leptonai.config import LEPTON_RESERVED_ENV_NAMES

from .api_resource import APIResourse
from .types.deployment import LeptonDeployment, TokenVar, Mount, EnvVar, EnvValue
from .types.events import LeptonEvent
from .types.readiness import ReadinessIssue
from .types.termination import DeploymentTerminations
from .types.replica import Replica


def make_token_vars_from_config(
    is_public: Optional[bool], tokens: Optional[List[str]]
) -> Optional[List[TokenVar]]:
    # Note that None is different from [] here. None means that the tokens are not
    # changed, while [] means that the tokens are cleared (aka, no tokens)

    if tokens is None and is_public is None:
        return None

    if is_public and not tokens:
        return []

    # Workspace token is no longer accessible
    final_tokens = []
    if tokens:
        final_tokens.extend([TokenVar(value=token) for token in tokens])
    return final_tokens


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
        parts = mount_str.split(":", 2)
        if len(parts) == 3:
            # TODO: Sanity check that this exists
            mount_list.append(
                Mount(
                    path=parts[0].strip(),
                    mount_path=parts[1].strip(),
                    **{"from": parts[2].strip()},
                ),
            )
        else:
            raise ValueError(
                f"Invalid mount definition: {mount_str} (expected format:"
                " STORAGE_PATH:MOUNT_PATH:MOUNT_FROM, where MOUNT_FROM is"
                " <type>:<storage_name> e.g. node-nfs:my-nfs, or node-local"
                " for node-local storage)"
            )
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


class DeploymentAPI(APIResourse):
    def _to_name(self, name_or_deployment: Union[str, LeptonDeployment]) -> str:
        return (  # type: ignore
            name_or_deployment
            if isinstance(name_or_deployment, str)
            else name_or_deployment.metadata.id_
        )

    def list_all(self):
        response = self._get("/deployments")
        return self.ensure_list(response, LeptonDeployment)

    def create(self, spec: LeptonDeployment):
        """
        Create a deployment with the given deployment spec.
        """
        response = self._post("/deployments", json=self.safe_json(spec))
        return self.ensure_ok(response)

    def create_pod(self, spec: LeptonDeployment):
        """
        Creates a pod with the given deployment spec. This is equivalent to creating a deployment
        with is_pod=True.
        """
        warnings.warn(
            "create_pod is deprecated. Use the api under leptonai.api.v1.pod"
            " instead, which is more explicit and gives more strict param checking.",
            DeprecationWarning,
        )
        if spec.spec is None:
            raise ValueError("LeptonDeploymentUserSpec must not be None.")
        spec.spec.is_pod = True
        # todo: pod-specific fields check if needed.
        return self.create(spec)

    def get(self, name_or_deployment: Union[str, LeptonDeployment]) -> LeptonDeployment:
        response = self._get(f"/deployments/{self._to_name(name_or_deployment)}")
        return self.ensure_type(response, LeptonDeployment)

    def update(
        self,
        name_or_deployment: Union[str, LeptonDeployment],
        spec: LeptonDeployment,
        dryrun: bool = False,
    ) -> LeptonDeployment:
        dryrun_param = "" if not dryrun else "?dryrun=true"

        response = self._patch(
            f"/deployments/{self._to_name(name_or_deployment)+dryrun_param}",
            json=self.safe_json(spec),
        )
        return self.ensure_type(response, LeptonDeployment)

    def stop(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> LeptonDeployment:
        """Scale the deployment down to zero replicas via PATCH.

        This issues a partial update equivalent to:
        {
          "spec": { "resource_requirement": { "min_replicas": 0 } }
        }
        """
        payload = {
            "spec": {
                "resource_requirement": {
                    "min_replicas": 0,
                }
            }
        }
        response = self._patch(
            f"/deployments/{self._to_name(name_or_deployment)}",
            json=payload,
        )
        return self.ensure_type(response, LeptonDeployment)

    def delete(self, name_or_deployment: Union[str, LeptonDeployment]) -> bool:
        response = self._delete(f"/deployments/{self._to_name(name_or_deployment)}")
        return self.ensure_ok(response)

    def restart(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> LeptonDeployment:
        response = self._put(
            f"/deployments/{self._to_name(name_or_deployment)}/restart"
        )
        return self.ensure_type(response, LeptonDeployment)

    def get_readiness(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> ReadinessIssue:
        response = self._get(
            f"/deployments/{self._to_name(name_or_deployment)}/readiness"
        )
        return self.ensure_type(response, ReadinessIssue)

    def get_termination(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> DeploymentTerminations:
        response = self._get(
            f"/deployments/{self._to_name(name_or_deployment)}/termination"
        )
        return self.ensure_type(response, DeploymentTerminations)

    def get_replicas(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> List[Replica]:
        response = self._get(
            f"/deployments/{self._to_name(name_or_deployment)}/replicas"
        )
        return self.ensure_list(response, Replica)

    def get_log(
        self,
        name_or_deployment: Union[str, LeptonDeployment],
        replica: Union[str, Replica],
        timeout: Optional[int] = None,
    ) -> Iterator[str]:
        """
        Gets the log of the given deployment's specified replica. The log is streamed
        in chunks until timeout is reached. If timeout is not specified, the log will be
        streamed indefinitely, although you should not rely on this behavior as connections
        can be dropped when streamed for a long time.
        """
        replica_id = replica if isinstance(replica, str) else replica.metadata.id_
        response = self._get(
            f"/deployments/{self._to_name(name_or_deployment)}/replicas/{replica_id}/log",
            stream=True,
            timeout=timeout,
        )
        if not response.ok:
            raise RuntimeError(
                f"API call failed with status code {response.status_code}. Details:"
                f" {response.text}"
            )
        for chunk in response.iter_content(chunk_size=None):
            if chunk:
                yield chunk.decode("utf8")

    def get_events(
        self, name_or_deployment: Union[str, LeptonDeployment]
    ) -> List[LeptonEvent]:
        response = self._get(f"/deployments/{self._to_name(name_or_deployment)}/events")
        return self.ensure_list(response, LeptonEvent)

    # TODO: implement api for the various metrics, but for now we will simply ask users
    # to view the metrics from the web portal.
