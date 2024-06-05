# todo
from typing import List, Union

from .api_resource import APIResourse

from .types.dedicated_node_group import DedicatedNodeGroup, Node


class DedicatedNodeGroupAPI(APIResourse):
    def _to_name(self, name_or_ng: Union[str, DedicatedNodeGroup]) -> str:
        return (  # type: ignore
            name_or_ng if isinstance(name_or_ng, str) else name_or_ng.metadata.id_
        )

    def list_all(self) -> List[DedicatedNodeGroup]:
        responses = self._get("/dedicated-node-groups")
        return self.ensure_list(responses, DedicatedNodeGroup)

    def get(self, name_or_ng: Union[str, DedicatedNodeGroup]) -> DedicatedNodeGroup:
        response = self._get(f"/dedicated-node-groups/{self._to_name(name_or_ng)}")
        return self.ensure_type(response, DedicatedNodeGroup)

    def list_nodes(self, name_or_ng: Union[str, DedicatedNodeGroup]) -> List[Node]:
        response = self._get(
            f"/dedicated-node-groups/{self._to_name(name_or_ng)}/nodes"
        )
        return self.ensure_list(response, Node)

    # todo: implement more node management and monitoring APIs
