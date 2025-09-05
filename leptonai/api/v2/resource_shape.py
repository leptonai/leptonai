from typing import Optional, List
from ..v1.api_resource import APIResourse
from .types.shape import Shape, ShapeSpec
from leptonai.api.v1.types.common import Metadata


class ResourceShapeAPI(APIResourse):
    def list_shapes(
        self, node_group: Optional[str] = None, purpose: Optional[str] = None
    ) -> List[Shape]:
        """
        Get resource shapes for the workspace.

        Args:
            node_group (Optional[str]): Name of the node group to filter shapes by
            purpose (Optional[str]): Purpose to filter shapes by (e.g., 'job', 'deployment')

        Returns:
            List[Shape]: List of available resource shapes

        Example:
            shapes = client.shapes.list_shapes(
                node_group="my-node-group",
                purpose="job"
            )
        """
        params = {}
        if node_group:
            params["node_groups"] = node_group
        if purpose:
            params["purpose"] = purpose

        response = self._get("/shapes", params=params)
        return self.ensure_list(response, Shape)
