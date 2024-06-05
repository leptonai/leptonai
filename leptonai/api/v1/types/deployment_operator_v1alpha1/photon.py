from pydantic import BaseModel
from typing import Optional, Dict, List


class PhotonDeploymentTemplate(BaseModel):
    resource_shape: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    secret: Optional[List[str]] = None


class PhotonStatus(BaseModel):
    system_photon: Optional[bool] = None
