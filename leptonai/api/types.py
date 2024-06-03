"""
Types for the Lepton AI API.

These types are used as wrappers of the json payloads used by the API.
"""

from enum import Enum
from typing import List, Optional, Union
import warnings
from pydantic import BaseModel, Field

from leptonai.config import LEPTON_RESERVED_ENV_NAMES, VALID_SHAPES


# Valid shapes is defined as a list instead of a dict intentionally, because
# we want to preserve the order of the shapes when printing. Granted, this
# adds a bit of search time, but the list is small enough that it should not
# matter.
DEFAULT_RESOURCE_SHAPE = "cpu.small"


def _get_valid_shapes_printout() -> str:
    """
    Utility function to get the valid shapes as a string.
    """
    if len(VALID_SHAPES) > 7:
        return ", ".join(VALID_SHAPES[:7]) + ", ..."
    return ", ".join(VALID_SHAPES)


# Spec to hold metadata
class Metadata(BaseModel):
    """
    The metadata of a deployment.
    """

    id_: Optional[str] = Field(None, alias="id")
    name: Optional[str] = None
    created_at: Optional[int] = None
    version: Optional[int] = None
    created_by: Optional[str] = None
    last_modified_by: Optional[str] = None


# Spec to hold resource requirements
class ResourceRequirement(BaseModel):
    resource_shape: Optional[str] = None

    # resource requirements per replica
    cpu: Optional[float] = None
    memory: Optional[int] = None
    accelerator_type: Optional[str] = None
    accelerator_num: Optional[float] = None
    ephemeral_storage_in_gb: Optional[int] = None

    resource_affinity: Optional[str] = None
    min_replicas: Optional[int] = None
    max_replicas: Optional[int] = None

    @staticmethod
    def make_resource_requirement(
        resource_shape: Optional[str] = None,
        replica_cpu: Optional[float] = None,
        replica_memory: Optional[int] = None,
        replica_accelerator_type: Optional[str] = None,
        replica_accelerator_num: Optional[float] = None,
        replica_ephemeral_storage_in_gb: Optional[int] = None,
        resource_affinity: Optional[str] = None,
        min_replicas: Optional[int] = None,
        max_replicas: Optional[int] = None,
    ) -> Optional["ResourceRequirement"]:
        """
        Validates the resource shape and min replicas, and returns a
        ResourceRequirement object.
        """
        if resource_shape is None and min_replicas is None:
            return None
        if resource_shape:
            resource_shape = resource_shape.lower()
            if resource_shape not in VALID_SHAPES:
                # We will check if the user passed in a valid shape, and if not, we will
                # print a warning.
                # However, we do not want to directly go to an error, because there might
                # be cases when the CLI and the cloud service is out of sync. For example
                # if the user environment has an older version of the CLI while the cloud
                # service has been updated to support more shapes, we want to allow the
                # user to use the new shapes. One can simply ignore the warning and proceed.
                warnings.warn(
                    "It seems that you passed in a non-standard resource shape"
                    f" {resource_shape}. Valid shapes supported by the CLI are:"
                    f" {_get_valid_shapes_printout()}."
                )
        if min_replicas is not None and min_replicas < 0:
            raise ValueError(
                f"min_replicas must be non-negative. Found {min_replicas}."
            )
        if max_replicas is not None and max_replicas < 0:
            raise ValueError(
                f"max_replicas must be non-negative. Found {max_replicas}."
            )
        if (
            min_replicas is not None
            and max_replicas is not None
            and min_replicas > max_replicas
        ):
            raise ValueError(
                "min_replicas must be smaller than max_replicas. Found"
                f" min_replicas={min_replicas}, max_replicas={max_replicas}."
            )
        # TODO: validate resource_affinity
        return ResourceRequirement(
            resource_shape=resource_shape,
            cpu=replica_cpu,
            memory=replica_memory,
            accelerator_type=replica_accelerator_type,
            accelerator_num=replica_accelerator_num,
            ephemeral_storage_in_gb=replica_ephemeral_storage_in_gb,
            resource_affinity=resource_affinity,
            min_replicas=min_replicas,
            max_replicas=max_replicas,
        )


class TokenValue(BaseModel):
    token_name_ref: str


class TokenVar(BaseModel):
    value: Optional[str] = None
    value_from: Optional[TokenValue] = None

    @staticmethod
    def public() -> List["TokenVar"]:
        return []

    @staticmethod
    def make_token_vars_from_config(
        is_public: Optional[bool], tokens: Optional[List[str]]
    ) -> Optional[List["TokenVar"]]:
        # Note that None is different from [] here. None means that the tokens are not
        # changed, while [] means that the tokens are cleared (aka, public deployment)
        if is_public is None and tokens is None:
            return None
        elif is_public and tokens:
            raise ValueError(
                "For access control, you cannot specify both is_public and token at the"
                " same time. Please specify either is_public=True with no tokens passed"
                " in, or is_public=False and tokens as a list."
            )
        else:
            if is_public:
                return TokenVar.public()
            else:
                final_tokens = [
                    TokenVar(value_from=TokenValue(token_name_ref="WORKSPACE_TOKEN"))
                ]
                if tokens:
                    final_tokens.extend([TokenVar(value=token) for token in tokens])
                return final_tokens


class EnvValue(BaseModel):
    secret_name_ref: str


class EnvVar(BaseModel):
    name: str
    value: Optional[str] = None
    value_from: Optional[EnvValue] = None

    @staticmethod
    def make_env_vars_from_strings(
        env: Optional[List[str]], secret: Optional[List[str]]
    ) -> Optional[List["EnvVar"]]:
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


class MountOptions(BaseModel):
    local_cache_size_mib: Optional[int] = None
    read_only: Optional[bool] = None


class Mount(BaseModel):
    path: Optional[str]
    from_: Optional[str] = Field(None, alias="from")
    mount_path: str
    mount_options: Optional[MountOptions] = None

    @staticmethod
    def make_mounts_from_strings(
        mounts: Optional[List[str]],
    ) -> Optional[List["Mount"]]:
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
                mount_list.append(
                    Mount(path=parts[0].strip(), mount_path=parts[1].strip())
                )
            else:
                raise ValueError(f"Invalid mount definition: {mount_str}")
        return mount_list


class ScaleDown(BaseModel):
    no_traffic_timeout: Optional[int] = None

    @staticmethod
    def make_scale_down(no_traffic_timeout: Optional[int] = None):
        if no_traffic_timeout is None:
            # None means no change to the scale down.
            return None
        elif no_traffic_timeout < 0:
            raise ValueError(
                f"no_traffic_timeout must be non-negative. Found {no_traffic_timeout}."
            )
        else:
            return ScaleDown(no_traffic_timeout=no_traffic_timeout)


class AutoScaler(BaseModel):
    scale_down: Optional[ScaleDown] = None
    target_gpu_utilization_percentage: Optional[int] = None

    @staticmethod
    def make_auto_scaler(
        no_traffic_timeout: Optional[int] = None,
        target_gpu_utilization: Optional[int] = None,
    ) -> Optional["AutoScaler"]:
        if no_traffic_timeout is None and target_gpu_utilization is None:
            # None means no change to the autoscaler.
            return None
        if no_traffic_timeout is not None and no_traffic_timeout < 0:
            raise ValueError(
                f"no_traffic_timeout must be non-negative. Found {no_traffic_timeout}."
            )
        if target_gpu_utilization is not None and (
            target_gpu_utilization < 0 or target_gpu_utilization > 100
        ):
            raise ValueError(
                "target_gpu_utilization must be between 0 and 100. Found"
                f" {target_gpu_utilization}."
            )
        return AutoScaler(
            scale_down=ScaleDown.make_scale_down(no_traffic_timeout=no_traffic_timeout),
            target_gpu_utilization_percentage=target_gpu_utilization,
        )


class HealthCheckLiveness(BaseModel):
    initial_delay_seconds: Optional[int] = None


class HealthCheck(BaseModel):
    liveness: Optional[HealthCheckLiveness] = None

    @staticmethod
    def make_health_check(
        initial_delay_seconds: Optional[int] = None,
    ) -> Optional["HealthCheck"]:
        if initial_delay_seconds is None:
            # None means no change to the health check.
            return None
        elif initial_delay_seconds < 0:
            raise ValueError(
                "initial_delay_seconds must be non-negative. Found"
                f" {initial_delay_seconds}."
            )
        else:
            return HealthCheck(
                liveness=HealthCheckLiveness(
                    initial_delay_seconds=initial_delay_seconds
                )
            )


class LeptonDeploymentState(str, Enum):
    Ready = "Ready"
    NotReady = "Not Ready"
    Starting = "Starting"
    Updating = "Updating"
    Deleting = "Deleting"
    Unknown = ""


class LeptonJobState(str, Enum):
    NotReady = "Not Ready"
    Running = "Running"
    Failed = "Failed"
    Completed = "Completed"
    Deleting = "Deleting"
    Unknown = ""


class LeptonJobStatus(BaseModel):
    """
    The observed state of a Lepton Job.
    """

    state: LeptonJobState
    ready: int
    active: int
    failed: int
    succeeded: int
    completion_time: Optional[int] = None


class ContainerPort(BaseModel):
    """
    The port spec of a Lepton Job.
    """

    @staticmethod
    def make_container_port(container_port: int, protocol: Optional[str] = None):
        if protocol and protocol.lower() not in ["tcp", "udp"]:
            raise ValueError(
                f"Invalid protocol: {protocol}. Protocol must be either tcp or udp."
            )
        return ContainerPort(container_port=container_port, protocol=protocol)

    @staticmethod
    def make_container_port_from_string(port_str: str):
        parts = port_str.split(":")
        if len(parts) == 2:
            try:
                port = int(parts[0].strip())
            except ValueError:
                raise ValueError(
                    f"Invalid port definition: {port_str}. Port must be an integer."
                )
            return ContainerPort(container_port=port, protocol=parts[1].strip())
        else:
            raise ValueError(f"Invalid port definition: {port_str}")

    container_port: int
    protocol: Optional[str] = None


class LeptonContainer(BaseModel):
    """
    The container spec of a Lepton Job.
    """

    image: Optional[str] = None
    ports: Optional[List[ContainerPort]] = None
    command: Optional[List[str]] = None

    @staticmethod
    def make_container(
        image: str,
        command: Union[str, List[str]],
        ports: Optional[List[str]] = None,
    ) -> "LeptonContainer":
        """
        Validates the container spec and returns a LeptonContainer object.
        """
        if not image:
            raise ValueError("image must be specified.")
        ports_list = (
            [
                ContainerPort.make_container_port_from_string(port_str)
                for port_str in ports
            ]
            if ports
            else None
        )
        if isinstance(command, str):
            # Implementation note: strictly speaking, we should use shlex.split here
            # to split the command string into a list of arguments. However, we are
            # not doing that as it may not be bullet proof.
            command = [command]
        return LeptonContainer(image=image, ports=ports_list, command=command)


class DeploymentUserSpec(BaseModel):
    photon_namespace: Optional[str] = None
    photon_id: Optional[str] = None
    container: Optional[LeptonContainer] = None
    resource_requirement: Optional[ResourceRequirement] = None
    auto_scaler: Optional[AutoScaler] = None
    api_tokens: Optional[List[TokenVar]] = None
    envs: Optional[List[EnvVar]] = None
    mounts: Optional[List[Mount]] = None
    pull_image_secrets: Optional[List[str]] = None
    health: Optional[HealthCheck] = None
    is_pod: Optional[bool] = None
    privileged: Optional[bool] = None


class AutoscalerCondition(BaseModel):
    status: str
    type_: str = Field(..., alias="type")
    last_transition_time: Optional[int] = None
    message: Optional[str] = None


class AutoScalerStatus(BaseModel):
    desired_replicas: Optional[int] = None
    last_transition_time: Optional[int] = None
    conditions: Optional[List[AutoscalerCondition]] = None


class DeploymentEndpoint(BaseModel):
    internal_endpoint: str
    external_endpoint: str
    custom_external_endpoint: Optional[List[str]] = None


class DeploymentStatus(BaseModel):
    state: LeptonDeploymentState
    endpoint: DeploymentEndpoint
    autoscaler_status: Optional[AutoScalerStatus] = None
    with_system_photon: Optional[bool] = None
    is_sysetm: Optional[bool] = None


class Deployment(BaseModel):
    """
    The main class that defines a deployment.
    """

    metadata: Optional[Metadata] = None
    spec: Optional[DeploymentUserSpec] = None
    status: Optional[DeploymentStatus] = None


class LeptonResourceAffinity(BaseModel):
    allowed_dedicated_node_groups: Optional[List[str]] = None


class LeptonJobSpec(BaseModel):
    """
    The desired state of a Lepton Job.
    """

    affinity: Optional[LeptonResourceAffinity] = None
    resource_shape: Optional[str] = None
    shared_memory_size: Optional[int] = None
    container: LeptonContainer = LeptonContainer()
    completions: int = 1
    parallelism: int = 1
    max_failure_retry: Optional[int] = None
    max_job_failure_retry: Optional[int] = None
    envs: List[EnvVar] = []
    mounts: List[Mount] = []
    image_pull_secrets: List[str] = []
    ttl_seconds_after_finished: Optional[int] = None
    intra_job_communication: Optional[bool] = None
    privileged: Optional[bool] = None


class LeptonMetadata(BaseModel):
    """
    The metadata of Lepton types.
    """

    id: str
    name: Optional[str] = None
    created_at: Optional[int] = None
    version: Optional[int] = None


class LeptonJob(BaseModel):
    """
    The Lepton Job.
    """

    metadata: LeptonMetadata
    spec: LeptonJobSpec
    status: Optional[LeptonJobStatus] = None
