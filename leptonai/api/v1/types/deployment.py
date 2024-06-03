from pydantic import BaseModel
from typing import Optional

from .common import Metadata

from .deployment_operator_v1alpha1.deployment import (
    LeptonDeploymentUserSpec,
    LeptonDeploymentStatus,
)

# Implementation note: because users do need to use the deployment specs' detailed
# classes, we import them all here.
from .deployment_operator_v1alpha1.deployment import *  # noqa: F401, F403


class LeptonDeployment(BaseModel):
    metadata: Optional[Metadata] = None
    spec: Optional[LeptonDeploymentUserSpec] = None
    status: Optional[LeptonDeploymentStatus] = None
