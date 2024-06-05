from pydantic import BaseModel


class TotalResource(BaseModel):
    cpu: float
    memory: int
    accelerator_num: float


class TotalService(BaseModel):
    kv_store_num: int
    queue_num: int
