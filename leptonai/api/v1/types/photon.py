from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from .deployment_operator_v1alpha1.photon import PhotonDeploymentTemplate, PhotonStatus


class Photon(BaseModel):
    # Implementation note: inlined MetadataV1
    id_: Optional[str] = Field(None, alias="id")
    created_at: Optional[int] = None
    version: Optional[int] = None

    # Implementation note: inlined PhotoSpec
    name: str
    model: str
    requirement_dependency: List[str]
    deployment_template: Optional[PhotonDeploymentTemplate] = None
    image: str
    cmd: Optional[List[str]] = None
    healthcheck_liveness_tcp_port: Optional[int] = None
    exposed_ports: Optional[List[int]] = None
    openapi_schema: Optional[Dict[str, Any]] = None
    is_deleted: Optional[bool] = None

    # Photon Status
    status: Optional[PhotonStatus] = None
