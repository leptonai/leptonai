from typing import Optional, Any, Literal
from pydantic import BaseModel

from leptonai.api.v1.types.common import Metadata


class LeptonTemplateUserSpec(BaseModel):
    content: Optional[Any] = None
    json_schema: Optional[Any] = None
    workload_type: Optional[Literal["job", "pod", "deployment"]] = None


class LeptonTemplateStatus(BaseModel):
    # Placeholder for status fields
    state: Optional[str] = None


class LeptonTemplate(BaseModel):
    metadata: Optional[Metadata] = None
    spec: Optional[LeptonTemplateUserSpec] = None
    status: Optional[LeptonTemplateStatus] = None
