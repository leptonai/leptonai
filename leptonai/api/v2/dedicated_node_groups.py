# todo
from typing import List, Union
from concurrent.futures import ThreadPoolExecutor

from ..v1.api_resource import APIResourse

from ..v1.types.dedicated_node_group import DedicatedNodeGroup, Node


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

    def list_idle_nodes(self, name_or_ng: Union[str, DedicatedNodeGroup]) -> List[Node]:
        response = self._get(
            f"/dedicated-node-groups/{self._to_name(name_or_ng)}/nodes",
            params={"idle": "true"},
        )
        return self.ensure_list(response, Node)

    # todo: implement more node management and monitoring APIs

    def batch_fetch_nodes(
        self,
        node_groups: List[Union[str, DedicatedNodeGroup]],
        concurrency: int = 8,
        return_exceptions: bool = False,
    ) -> List[Union[List[Node], Exception]]:
        """
        Fetch nodes for multiple dedicated node groups concurrently.

        - Preserves input order: the i-th result corresponds to the i-th input.
        - Raises on any fetch error (do not swallow), letting callers decide how to handle.

        Args:
            node_groups: A list of node group identifiers or objects.
            concurrency: Max number of concurrent requests.

        Returns:
            When return_exceptions is False: List of node lists, aligned to input order.
            When return_exceptions is True:  List aligned to input order, each item is either List[Node] or Exception.
        """
        if not node_groups:
            return []

        max_workers = min(max(1, concurrency), len(node_groups))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            if not return_exceptions:
                results_no_exc: List[List[Node]] = []
                for nodes in executor.map(self.list_nodes, node_groups):
                    results_no_exc.append(nodes)
                return results_no_exc
            else:
                futures = [executor.submit(self.list_nodes, ng) for ng in node_groups]
                results_mixed: List[Union[List[Node], Exception]] = []
                for fut in futures:
                    try:
                        results_mixed.append(fut.result())
                    except Exception as e:
                        results_mixed.append(e)
                return results_mixed
