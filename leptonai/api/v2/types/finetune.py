from typing import Optional, Any, List
from pydantic import BaseModel

from leptonai.api.v1.types.common import Metadata
from leptonai.api.v1.types.job import LeptonJobUserSpec, LeptonJobStatus
from leptonai.api.v1.types.deployment import Mount


class TechniqueInfo(BaseModel):
    # nil = unknown, true = supported, false = not supported
    is_supported: Optional[bool] = None


class FineTuneModelInfo(BaseModel):
    # Hugging Face model ID
    model_id: str
    sft: TechniqueInfo
    lora: TechniqueInfo


class TrainerInfo(BaseModel):
    trainer_id: str
    is_default: bool


class Trainer(BaseModel):
    # If not specified, the default trainer will be used.
    # We currently only support Nemo AutoModel but allow different versions for testing.
    id: Optional[str] = None
    # Configuration for training with the trainer (hyperparameters etc.)
    train_config: Optional[Any] = None


class LatestCheckpointInfo(BaseModel):
    mount: Optional[Mount] = None
    path: Optional[str] = None


class LeptonFineTuneJobStatus(LeptonJobStatus):
    latest_checkpoint_info: Optional[LatestCheckpointInfo] = None


class LeptonFineTuneJobSpec(LeptonJobUserSpec):
    trainer: Optional[Trainer] = None


class LeptonFineTuneJob(BaseModel):
    metadata: Metadata
    spec: LeptonFineTuneJobSpec = LeptonFineTuneJobSpec()
    status: Optional[LeptonFineTuneJobStatus] = None


class LeptonFineTuneJobList(BaseModel):
    finetune_jobs: List[LeptonFineTuneJob]
