from pydantic import BaseModel
from typing import Optional, List


class LeptonResourceAffinity(BaseModel):
    """
    Affinity is a group of affinity scheduling rules.
    """

    # Kubernetes label selector over visible user node labels. Batch jobs only.
    # Empty means no extra constraint. Mutually exclusive with an explicit node allowlist.
    node_label_selector: Optional[str] = None
    allowed_providers: Optional[List[str]] = None
    allowed_dedicated_node_groups: Optional[List[str]] = None
    allowed_nodes_in_node_group: Optional[List[str]] = None
