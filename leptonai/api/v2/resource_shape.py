from typing import Optional, List
from ..v1.api_resource import APIResourse
from ..v2.types.workspace import ResourceShape


class ResourceShapeAPI(APIResourse):
    def ensure_resource_shape(self, response):
        self._raise_if_not_ok(response)

        valid_items = []
        errors: List[str] = []
        items_raw = response.json()

        for idx, raw in enumerate(items_raw):
            try:
                metadata = raw.get("metadata", {})
                spec = raw.get("spec", {})
                valid_items.append(ResourceShape(**metadata, **spec))
            except Exception as e:
                errors.append(f"\n index {idx}: {e}\nitem: {raw}")

        if errors:
            import sys

            sys.stderr.write(
                f"[lepton-error] Skipped {len(errors)} invalid item(s) when parsing"
                " list response:"
                + "".join(errors)
                + "\n"
            )

        return valid_items

    def list_shapes(
        self, 
        node_group: Optional[str] = None, 
        purpose: Optional[str] = None
    ) -> List[ResourceShape]:
        """
        Get resource shapes for the workspace.
        
        Args:
            node_group (Optional[str]): Name of the node group to filter shapes by
            purpose (Optional[str]): Purpose to filter shapes by (e.g., 'job', 'deployment')
            
        Returns:
            List[ResourceShape]: List of available resource shapes
            
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
        return self.ensure_resource_shape(response)
