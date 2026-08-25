"""
Helpers that build pieces of a deployment spec from human-friendly string
inputs (e.g. CLI flags). These are shared by the endpoint, pod, job, finetune,
and raycluster commands, so they live here rather than in any single API module.
"""

import re
from typing import List, Optional

from leptonai.config import LEPTON_RESERVED_ENV_NAMES

from .types.deployment import (
    Mount,
    EnvVar,
    EnvValue,
    StorageAttachment,
    DataSourceAttachment,
)


_ENVIRONMENT_VARIABLE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def validate_environment_variable_name(name: str, *, is_secret: bool = False) -> None:
    """Validate an environment variable name used by a workload."""
    if not isinstance(name, str) or not name:
        raise ValueError("Environment variable name cannot be empty.")
    if "0" <= name[0] <= "9":
        raise ValueError("Environment variable name cannot start with a digit.")
    if _ENVIRONMENT_VARIABLE_NAME_PATTERN.fullmatch(name) is None:
        raise ValueError(
            "Environment variable name can contain only letters, digits, hyphens, "
            "underscores, and periods."
        )
    if name in LEPTON_RESERVED_ENV_NAMES:
        name_type = "secret" if is_secret else "environment variable"
        raise ValueError(
            f"You have used a reserved {name_type} name that is "
            f"used by Lepton internally: {name}. Please use a different name. "
            "Here is a list of all reserved environment variable names:\n"
            f"{LEPTON_RESERVED_ENV_NAMES}"
        )


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


_STORAGE_ATTACHMENT_MODES = ("awsProfile", "mscProfile")
_STORAGE_ATTACHMENT_ATTACH_WITH_VALUES = ("object", "object.aistore")


def _storage_attachment_definition_error(spec_str: str, detail: str) -> ValueError:
    return ValueError(
        f"Invalid storage attachment definition: {spec_str} ({detail}; expected"
        " DATA_SOURCE_NAME:MODE[:ATTACH_WITH[:PROFILE_NAME]], where MODE is one of"
        f" {', '.join(_STORAGE_ATTACHMENT_MODES)} and ATTACH_WITH, if given, is one"
        f" of {', '.join(_STORAGE_ATTACHMENT_ATTACH_WITH_VALUES)})"
    )


def make_storage_attachments_from_strings(
    storage_attachments: Optional[List[str]],
) -> Optional[List[StorageAttachment]]:
    """
    Parses a list of storage attachment strings into a list of StorageAttachment
    objects. Multiple entries for the same DATA_SOURCE_NAME are merged into one
    StorageAttachment with multiple attachments, preserving first-seen order.
    """
    if not storage_attachments:
        return None
    attachments_by_data_source: "dict[str, List[DataSourceAttachment]]" = {}
    for spec_str in storage_attachments:
        parts = spec_str.split(":", 3)
        if len(parts) < 2:
            raise _storage_attachment_definition_error(
                spec_str, "expected at least DATA_SOURCE_NAME:MODE"
            )
        data_source_name = parts[0].strip()
        mode = parts[1].strip()
        attach_with = parts[2].strip() if len(parts) > 2 else ""
        profile_name = parts[3].strip() if len(parts) > 3 else ""

        if not data_source_name:
            raise _storage_attachment_definition_error(
                spec_str, "DATA_SOURCE_NAME cannot be empty"
            )
        if mode not in _STORAGE_ATTACHMENT_MODES:
            raise _storage_attachment_definition_error(
                spec_str,
                f"MODE must be one of {', '.join(_STORAGE_ATTACHMENT_MODES)}, found"
                f" `{mode}`",
            )
        if attach_with and attach_with not in _STORAGE_ATTACHMENT_ATTACH_WITH_VALUES:
            raise _storage_attachment_definition_error(
                spec_str,
                "ATTACH_WITH must be one of"
                f" {', '.join(_STORAGE_ATTACHMENT_ATTACH_WITH_VALUES)}, found"
                f" `{attach_with}`",
            )

        attachments_by_data_source.setdefault(data_source_name, []).append(
            DataSourceAttachment(
                mode=mode,
                attach_with=attach_with or None,
                profile_name=profile_name or None,
            )
        )

    return [
        StorageAttachment(data_source_name=name, attachments=attachments)
        for name, attachments in attachments_by_data_source.items()
    ]


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
        validate_environment_variable_name(k)
        env_list.append(EnvVar(name=k, value=v))
    for s in secret if secret else []:
        # We provide the user a shorcut: instead of having to specify
        # SECRET_NAME=SECRET_NAME, they can just specify SECRET_NAME
        # if the local env name and the secret name are the same.
        k, v = s.split("=", 1) if "=" in s else (s, s)
        validate_environment_variable_name(k, is_secret=True)
        # TODO: sanity check if these secrets exist.
        env_list.append(EnvVar(name=k, value_from=EnvValue(secret_name_ref=v)))
    return env_list
