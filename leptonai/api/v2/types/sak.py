from pydantic import BaseModel, Field
from typing import List


class ListSAKResponseElement(BaseModel):
    """
    SAK list response element.
    """

    id_: str = Field(alias="id")
    name: str
    masked_value: str
    scopes: List[str]
    created_at: int
    expires_at: int
    created_by: str


class CreateSAKRequest(BaseModel):
    """
    SAK creation request body.
    """

    name: str
    scopes: List[str]
    expires_in: int
