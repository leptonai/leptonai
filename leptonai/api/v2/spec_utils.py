"""
Helpers that build pieces of a deployment spec from human-friendly string
inputs (e.g. CLI flags). These are shared by the endpoint, pod, job, finetune,
and raycluster commands, so they live here rather than in any single API module.
"""

from typing import List, Optional

from leptonai.config import LEPTON_RESERVED_ENV_NAMES

from .types.deployment import Mount, EnvVar, EnvValue


def _mount_definition_error(mount_str: str, detail: str) -> ValueError:
    return ValueError(
        f"Invalid mount definition: {mount_str} ({detail}; expected"
        " FROM_PATH:MOUNT_PATH:VOLUME, where VOLUME is `node-local`"
        " or `node-<type>:<storage_name>`, e.g. node-nfs:my-nfs)"
    )


def _validate_mount_from(mount_str: str, mount_from: str) -> str:
    if not mount_from:
        raise _mount_definition_error(mount_str, "VOLUME cannot be empty")

    if mount_from == "node-local":
        return mount_from

    if not mount_from.startswith("node-"):
        return mount_from

    mount_from_parts = mount_from.split(":")
    if len(mount_from_parts) == 1:
        raise _mount_definition_error(
            mount_str,
            f"missing storage_name in VOLUME `{mount_from}`",
        )
    if len(mount_from_parts) != 2:
        raise _mount_definition_error(
            mount_str,
            f"VOLUME `{mount_from}` must contain exactly one colon after `node-<type>`",
        )

    storage_type = mount_from_parts[0][len("node-") :].strip()
    storage_name = mount_from_parts[1].strip()
    if not storage_type:
        raise _mount_definition_error(
            mount_str,
            f"missing storage type in VOLUME `{mount_from}`",
        )
    if not storage_name:
        raise _mount_definition_error(
            mount_str,
            f"missing storage_name in VOLUME `{mount_from}`",
        )

    return mount_from


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
            mount_from = _validate_mount_from(mount_str, parts[2].strip())
            # TODO: Sanity check that this exists
            mount_list.append(
                Mount(
                    path=parts[0].strip(),
                    mount_path=parts[1].strip(),
                    **{"from": mount_from},
                ),
            )
        else:
            raise _mount_definition_error(
                mount_str,
                "expected FROM_PATH:MOUNT_PATH:VOLUME split on the first two colons",
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
