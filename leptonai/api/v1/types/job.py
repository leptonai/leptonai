from pydantic import BaseModel, Field
from typing import Optional

from .common import Metadata
from .deployment_operator.v1alpha1.job import LeptonJobUserSpec, LeptonJobStatus


class LeptonJob(BaseModel):
    metadata: Metadata
    spec: LeptonJobUserSpec = LeptonJobUserSpec()
    status: Optional[LeptonJobStatus] = None
