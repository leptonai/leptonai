import warnings
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List

from leptonai.config import compatible_field_validator, v2only_field_validator

from .affinity import LeptonResourceAffinity
from .common import Metadata

from enum import Enum

from .deployment import EnvVar
from .job import LeptonJobUserSpec


class TrainingState(Enum):
    Training = "Training"
    Ready = "Ready"
    Running = "Running"
    Updating = "Updating"
    Stopped = "Stopped"
    Failed = "Failed"


class L3MOptions:
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



class TunaModelSpec:
    envs: List[EnvVar] = []
    job_spec: Optional[LeptonJobUserSpec] = None
    deployment_spec: Optional[] = None
    model_path: Optional[str] = None
    l3m_optons: Optional[L3MOptions] = None
    dataset_path: Optional[str] = None
    model_output_path: Optional[str] = None




class TunaModel(BaseModel):
    metadata: Optional[Metadata] = None
    spec: Optional[TunaModelSpec] = None
    status: Optional[TunaModelStatus] = None

