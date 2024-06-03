from pydantic import BaseModel
from typing import Optional

from .common import Metadata
from .deployment_operator_v1alpha1.job import LeptonJobUserSpec, LeptonJobStatus
from .deployment_operator_v1alpha1.job import *  # noqa: F401, F403


class LeptonJob(BaseModel):
    metadata: Metadata
    spec: LeptonJobUserSpec = LeptonJobUserSpec()
    status: Optional[LeptonJobStatus] = None
