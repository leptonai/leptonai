from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Union, Dict, Any
from loguru import logger

from .common import Metadata
from .auth import AuthConfig


class LeastRequestLoadBalancer(BaseModel):
    choice_count: Optional[int] = None


class LoadBalanceConfig(BaseModel):
    least_request: Optional[LeastRequestLoadBalancer] = None
    maglev: Optional["MaglevLoadBalancer"] = None


class MaglevLoadBalancer(BaseModel):
    # Use hostname instead of resolved IP for hashing
    use_hostname_for_hashing: Optional[bool] = Field(
        default=None, alias="useHostnameForHashing"
    )


class LeptonIngressEndpoint(BaseModel):
    deployment: Optional[str] = None
    weight: Optional[int] = None
    load_balance_config: Optional[Union[LoadBalanceConfig, Dict[str, Any]]] = None


class WorkspaceTierRateLimiter(BaseModel):
    pass


class RateLimitConfig(BaseModel):
    workspace_tier_ratelimiter: Optional[WorkspaceTierRateLimiter] = None


class LeptonIngressLocality(BaseModel):
    region: Optional[str] = None


class TrafficShadowingConfig(BaseModel):
    percentage: Optional[int] = None
    endpoint: Optional[LeptonIngressEndpoint] = None


class LeptonIngressUserSpec(BaseModel):
    """
    The user spec of a Lepton Ingress.
    """

    domain_name: str
    endpoints: Optional[List[LeptonIngressEndpoint]] = None
    retelimit_config: Optional[RateLimitConfig] = None
    auth_config: Optional[AuthConfig] = None
    locality: Optional[LeptonIngressLocality] = None
    traffic_shadowing_config: Optional[TrafficShadowingConfig] = None


class CustomDomainValidationStatus(str, Enum):
    Pending = "pending"
    Active = "active"
    Failed = "failed"
    Unknown = "unknown"

    @classmethod
    def _missing_(cls, value):
        logger.trace(f"Unknown value: {value} for CustomDomainValidationStatus")
        return cls.Unknown


class LeptonIngressStatus(BaseModel):
    """
    The status of a Lepton Ingress.
    """

    # Implementation note: inlined v1alpha1.LeptonIngressStatus in the backend.
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
