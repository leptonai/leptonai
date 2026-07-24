from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .common import Metadata


class ObjectStorageProviderConfig(BaseModel):
    type_: str = Field(..., alias="type")
    aws: Optional[Dict[str, Any]] = None
    s3: Optional[Dict[str, Any]] = None
    gcs: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, str]] = None


class ObjectStorageConfig(BaseModel):
    bucket: str
    provider: ObjectStorageProviderConfig
    credentials: Optional[Dict[str, Any]] = None
    pvc: Optional[Dict[str, Any]] = None
    aistore: Optional[Dict[str, Any]] = None


class DataSourcePermissions(BaseModel):
    allowed_users: Optional[List[str]] = None


class StorageDataSourceSpec(BaseModel):
    name: str
    workspace: str
    description: Optional[str] = None
    object_: ObjectStorageConfig = Field(..., alias="object")
    permissions: Optional[DataSourcePermissions] = None


class StorageDataSourceStatus(BaseModel):
    state: Optional[str] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    summary: Optional[str] = None
    ready: Optional[bool] = None
    pvcs: Optional[List[Dict[str, Any]]] = None
    aistore: Optional[Dict[str, Any]] = None
    k8s_secret_name: Optional[str] = Field(None, alias="k8sSecretName")
    aistore_k8s_secret_name: Optional[str] = Field(
        None,
        alias="aistoreK8sSecretName",
    )
    observed_generation: Optional[int] = Field(None, alias="observedGeneration")


class StorageDataSource(BaseModel):
    metadata: Metadata
    spec: StorageDataSourceSpec
    status: StorageDataSourceStatus
