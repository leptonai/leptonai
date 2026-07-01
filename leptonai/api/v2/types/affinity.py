from pydantic import BaseModel
from typing import Optional, List


class LeptonResourceAffinity(BaseModel):
    """
    Affinity is a group of affinity scheduling rules.
    """

    allowed_providers: Optional[List[str]] = None
    allowed_dedicated_node_groups: Optional[List[str]] = None
    allowed_nodes_in_node_group: Optional[List[str]] = None
