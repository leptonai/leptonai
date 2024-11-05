import warnings
from pydantic import BaseModel
from typing import Optional, List
from .common import Metadata

from enum import Enum

from .deployment import LeptonDeploymentUserSpec
from .job import LeptonJobUserSpec


class TrainingState(str, Enum):
    Training = "Training"
    Ready = "Ready"
    Running = "Running"
    Updating = "Updating"
    Stopped = "Stopped"
    Failed = "Failed"
    Unknown = "UNK"

    @classmethod
    def _missing_(cls, value):
        if value:
            warnings.warn("You might be using an out of date SDK. consider updating.")
        return cls.Unknown


class L3MOptions(BaseModel):
    lora: Optional[bool] = None
    medusa: Optional[bool] = None
    lora_rank: Optional[int] = None
    lora_alpha: Optional[int] = None
    lora_dropout: Optional[float] = None
    report_wandb: Optional[bool] = None
    warmup_ratio: Optional[float] = None
    learning_rate: Optional[float] = None
    wandb_project: Optional[str] = None
    num_train_epochs: Optional[int] = None
    early_stop_threshold: Optional[float] = None
    gradient_accumulation_steps: Optional[int] = None
    per_device_train_batch_size: Optional[int] = None
    purpose: Optional[str] = None
    model_max_length: Optional[int] = None
    num_medusa_head: Optional[int] = None

    class Config:
        protected_namespaces = ()


class TunaModelSpec(BaseModel):
    job_spec: Optional[LeptonJobUserSpec] = None
    deployment_spec: Optional[LeptonDeploymentUserSpec] = None
    model_path: Optional[str] = None
    l3m_options: Optional[L3MOptions] = None
    dataset_path: Optional[str] = None
    model_output_path: Optional[str] = None

    class Config:
        protected_namespaces = ()


class TunaModelStatus(BaseModel):
    state: Optional[TrainingState] = None
    training_jobs: Optional[List[str]] = None
    deployments: Optional[List[str]] = None


class TunaModel(BaseModel):
    metadata: Optional[Metadata] = None
    spec: Optional[TunaModelSpec] = None
    status: Optional[TunaModelStatus] = None
