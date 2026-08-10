"""Client-side validation for jobs before they are sent to the API."""

import posixpath
import re
from typing import Optional

from .spec_utils import validate_environment_variable_name
from .types.job import LeptonJob


MAX_JOB_NAME_LENGTH = 36
MAX_LABEL_KEY_LENGTH = 63

LEPTON_RESERVED_MOUNT_PATHS = frozenset({
    "/",
    "/bin",
    "/boot",
    "/dev",
    "/etc",
    "/lib",
    "/lib64",
    "/media",
    "/opt",
    "/proc",
    "/run",
    "/sbin",
    "/srv",
    "/sys",
    "/usr",
    "/usr/bin",
    "/usr/lib",
    "/usr/local",
    "/usr/sbin",
    "/var",
    "/sys/fs/cgroup",
    "/sys/kernel/security",
    "/proc/sys",
    "/proc/bus",
})

_JOB_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
_LABEL_KEY_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")


def validate_job_name(name: str) -> None:
    """Validate a user-provided Job name."""
    if not isinstance(name, str) or not name:
        raise ValueError("Job name cannot be empty.")
    if len(name) > MAX_JOB_NAME_LENGTH:
        raise ValueError(
            f"Job name must be at most {MAX_JOB_NAME_LENGTH} characters long."
        )
    if not ("a" <= name[0] <= "z"):
        raise ValueError("Job name must start with a lowercase letter.")
    if _JOB_NAME_PATTERN.fullmatch(name) is None:
        raise ValueError(
            "Job name can contain only lowercase letters, digits, and hyphens."
        )
    if name.endswith("-"):
        raise ValueError("Job name cannot end with a hyphen.")
    if name.endswith("by-lepton"):
        raise ValueError("Job name cannot end with 'by-lepton'.")


def _normalize_mount_path(path: str) -> str:
    normalized = posixpath.normpath(path)
    # POSIX preserves exactly two leading slashes. Container mount paths do not
    # need that distinction, and collapsing them prevents reserved-path bypasses.
    if normalized.startswith("//"):
        normalized = "/" + normalized.lstrip("/")
    return normalized


def validate_mount_path(path: str) -> None:
    """Reject exact system mount paths after POSIX path normalization.

    Descendants are intentionally allowed. For example, ``/var`` is reserved,
    while ``/var/data`` is not an exact member of the reserved-path set.
    """
    if not isinstance(path, str):
        raise ValueError("Mount path must be a string.")
    if _normalize_mount_path(path) in LEPTON_RESERVED_MOUNT_PATHS:
        raise ValueError(
            f"Mount path '{path}' is reserved by Lepton and cannot be used."
        )


def validate_label_key(key: str) -> None:
    """Validate a Job metadata label key."""
    if not isinstance(key, str) or not key:
        raise ValueError("Label key cannot be empty.")
    if len(key) > MAX_LABEL_KEY_LENGTH:
        raise ValueError(
            f"Label key must be at most {MAX_LABEL_KEY_LENGTH} characters long."
        )
    if _LABEL_KEY_PATTERN.fullmatch(key) is None:
        raise ValueError(
            "Label key must start and end with a letter or digit and can contain "
            "only letters, digits, periods, underscores, and hyphens."
        )


def _validate_positive_worker_count(name: str, value: Optional[int]) -> None:
    if value is not None and (isinstance(value, bool) or value <= 0):
        raise ValueError(f"Job {name} must be a positive integer.")


def validate_job_create(job: LeptonJob) -> None:
    """Validate Job fields immediately before creation."""
    name = job.metadata.id_ if job.metadata.id_ is not None else job.metadata.name or ""
    validate_job_name(name)

    for env_var in job.spec.envs or []:
        validate_environment_variable_name(env_var.name)

    for mount in job.spec.mounts or []:
        validate_mount_path(mount.mount_path)

    for label_key in (job.metadata.labels or {}).keys():
        validate_label_key(label_key)

    _validate_positive_worker_count("completions", job.spec.completions)
    _validate_positive_worker_count("parallelism", job.spec.parallelism)
