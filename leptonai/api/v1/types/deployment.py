from pydantic import BaseModel, Field
from typing import Optional

from .common import Metadata
from .deployment_operator.v1alpha1.deployment import (
    LeptonDeploymentUserSpec,
    LeptonDeploymentStatus,
)


class LeptonDeployment(BaseModel):
    metadata: Optional[Metadata] = None
    spec: Optional[LeptonDeploymentUserSpec] = None
    status: Optional[LeptonDeploymentStatus] = None
