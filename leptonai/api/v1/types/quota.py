from pydantic import BaseModel


class TotalResource(BaseModel):
    cpu: float
    memory: int
    accelerator_num: float
