from pydantic import BaseModel, Field
from typing import Optional

from .common import Metadata

# Implementation note: because users do need to use the deployment specs' detailed
# classes, we import them all here.
from .deployment_operator.v1alpha1.deployment import *  # noqa: F401


class LeptonDeployment(BaseModel):
    metadata: Optional[Metadata] = None
    spec: Optional[LeptonDeploymentUserSpec] = None
    status: Optional[LeptonDeploymentStatus] = None
