# flake8: noqa
"""
Types for the Lepton AI API.

These types are used as wrappers of the json payloads used by the API.
"""

from enum import Enum
from typing import List, Optional, Union
import warnings
from pydantic import BaseModel, Field

from leptonai.config import LEPTON_RESERVED_ENV_NAMES, VALID_SHAPES

from ..v1.types.common import Metadata

from ..v1.types.deployment import (
    ResourceRequirement,
    TokenValue,
    TokenVar,
    EnvValue,
    EnvVar,
    MountOptions,
    Mount,
    ScaleDown,
    AutoScaler,
    HealthCheckLiveness,
    HealthCheck,
    LeptonDeploymentState,
    ContainerPort,
    LeptonContainer,
    AutoscalerCondition,
    AutoScalerStatus,
    LeptonResourceAffinity,
)

from ..v1.types.deployment import (
    LeptonDeploymentUserSpec as DeploymentUserSpec,
    DeploymentEndpoint,
    LeptonDeploymentStatus as DeploymentStatus,
    LeptonDeployment as Deployment,
)

from ..v1.types.job import LeptonJob, LeptonJobUserSpec, LeptonJobState, LeptonJobStatus


warnings.warn(
    "the leptonai.api.types module is deprecated. Use leptonai.api.v1.types for a"
    " more fine grained API service. This backward compatible code might be removed"
    " in the future.",
    DeprecationWarning,
    stacklevel=2,
)
