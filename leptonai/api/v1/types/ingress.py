from pydantic import BaseModel
from typing import Optional

from .common import Metadata
from .deployment_operator_v1alpha1.ingress import (
    LeptonIngressUserSpec,
    CustomDomainValidationStatus,
)


class LeptonIngressStatus(BaseModel):
    """
    The status of a Lepton Ingress.
    """

    # Inlined v1alpha1.LeptonIngressStatus
    validation_status: Optional[CustomDomainValidationStatus] = None
    message: Optional[str] = None
    # additional properties
    expected_cname_target: Optional[str] = None
    expected_dns01_channelge_target: Optional[str] = None


class LeptonIngress(BaseModel):
    metadata: Metadata
    spec: LeptonIngressUserSpec
    status: Optional[LeptonIngressStatus] = None
    expected_cname_target: Optional[str] = None
    expected_dns01_channelge_target: Optional[str] = None
