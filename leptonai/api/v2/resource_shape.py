from typing import Optional, List
from ..v1.api_resource import APIResourse
from .types.shape import Shape


class ResourceShapeAPI(APIResourse):
    def list_shapes(
        self, node_group: Optional[str] = None, purpose: Optional[str] = None
    ) -> List[Shape]:
        """List resource shapes.

        Args:
            node_group: Optional node group name filter.
            purpose: Optional purpose filter (e.g. deployment|pod|job).

        Returns:
            List[Shape]: Available resource shapes.
        """
        params = {}
        if node_group:
            params["node_groups"] = node_group
        if purpose:
            params["purpose"] = purpose

        response = self._get("/shapes", params=params)
        return self.ensure_list(response, Shape)
