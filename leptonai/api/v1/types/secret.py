from typing import Optional, List

from pydantic import BaseModel, Field

from .common import LeptonVisibility


class SecretItem(BaseModel):
    """
    Secret item definition for v1 API.

    Fields mirror the server-side schema:
    - name: Secret name (identifier)
    - value: Secret value (write-only; omitted in responses)
    - tags: Optional labels for categorization
    - owner: Owner identifier
    - visibility: Resource visibility
    """

    name: str = Field(alias="name")
    value: Optional[str] = Field(default=None, alias="value")
    tags: Optional[List[str]] = Field(default=None, alias="tags")
    owner: Optional[str] = Field(default=None, alias="owner")
    visibility: Optional[LeptonVisibility] = Field(default=None, alias="visibility")
