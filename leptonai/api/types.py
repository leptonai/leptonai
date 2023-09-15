"""
Types for the Lepton AI API.

These types are used as wrappers of the json payloads used by the API.
"""

from typing import List, Optional
import warnings
from pydantic import BaseModel

from leptonai.config import LEPTON_RESERVED_ENV_PREFIX


# Valid shapes is defined as a list instead of a dict intentionally, because
# we want to preserve the order of the shapes when printing. Granted, this
# adds a bit of search time, but the list is small enough that it should not
# matter.
VALID_SHAPES = ["cpu.small", "cpu.medium", "cpu.large", "gpu.t4", "gpu.a10"]
DEFAULT_RESOURCE_SHAPE = "cpu.small"


def _get_valid_shapes_printout() -> str:
    """
    Utility function to get the valid shapes as a string.
    """
    if len(VALID_SHAPES) > 7:
        return ", ".join(VALID_SHAPES[:7]) + ", ..."
    return ", ".join(VALID_SHAPES)


# Spec to hold resource requirements
class ResourceRequirement(BaseModel):
    resource_shape: Optional[str] = None
    resource_affinity: Optional[str] = None
    min_replicas: Optional[int] = None

    @staticmethod
    def make_resource_requirement(
        resource_shape: Optional[str] = None,
        resource_affinity: Optional[str] = None,
        min_replicas: Optional[int] = None,
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
                    " {resource_shape}. Valid shapes supported by the CLI are:"
                    f" {_get_valid_shapes_printout()}."
                )
        if min_replicas is not None and min_replicas < 0:
            raise ValueError(
                f"min_replicas must be non-negative. Found {min_replicas}."
            )
        # TODO: validate resource_affinity
        return ResourceRequirement(
            resource_shape=resource_shape,
            resource_affinity=resource_affinity,
            min_replicas=min_replicas,
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
                "Cannot specify both is_public and token at the same time."
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
            if k.lower().startswith(LEPTON_RESERVED_ENV_PREFIX):
                raise ValueError(
                    "Environment variable name cannot start with reserved prefix"
                    f" {LEPTON_RESERVED_ENV_PREFIX}. Found {k}."
                )
            env_list.append(EnvVar(name=k, value=v))
        for s in secret if secret else []:
            # We provide the user a shorcut: instead of having to specify
            # SECRET_NAME=SECRET_NAME, they can just specify SECRET_NAME
            # if the local env name and the secret name are the same.
            k, v = s.split("=", 1) if "=" in s else (s, s)
            if k.lower().startswith(LEPTON_RESERVED_ENV_PREFIX):
                raise ValueError(
                    "Secret name cannot start with reserved prefix"
                    f" {LEPTON_RESERVED_ENV_PREFIX}. Found {k}."
                )
            # TODO: sanity check if these secrets exist.
            env_list.append(EnvVar(name=k, value_from=EnvValue(secret_name_ref=v)))
        return env_list


class Mount(BaseModel):
    path: str
    mount_path: str

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


class AutoScaler(BaseModel):
    scale_down: Optional[ScaleDown] = None

    @staticmethod
    def make_auto_scaler(
        no_traffic_timeout: Optional[int] = None,
    ) -> Optional["AutoScaler"]:
        if no_traffic_timeout is None:
            # None means no change to the autoscaler.
            return None
        elif no_traffic_timeout < 0:
            raise ValueError(
                f"no_traffic_timeout must be non-negative. Found {no_traffic_timeout}."
            )
        elif no_traffic_timeout == 0:
            # timeout of 0 means explicitly set no timeout.
            return AutoScaler(scale_down=ScaleDown(no_traffic_timeout=0))
        else:
            return AutoScaler(
                scale_down=ScaleDown(no_traffic_timeout=no_traffic_timeout)
            )


# Spec to hold deployment configurations
class DeploymentSpec(BaseModel):
    """
    The main class that defines the deployment spec.
    """

    name: str
    photon_id: Optional[str] = None
    resource_requirement: Optional[ResourceRequirement] = None
    auto_scaler: Optional[AutoScaler] = None
    api_tokens: Optional[List[TokenVar]] = None
    envs: Optional[List[EnvVar]] = None
    mounts: Optional[List[Mount]] = None
