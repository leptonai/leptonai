# todo
from typing import List, Union
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

from .api_resource import APIResourse

from .types.dedicated_node_group import DedicatedNodeGroup, Node, Volume
from .types.node_reservation import NodeReservation
from .types.storage_data_source import StorageDataSource, StorageDataSourceSpec
from .types.storage_permission import StoragePermission


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

    def list_reservations(
        self, name_or_ng: Union[str, DedicatedNodeGroup]
    ) -> List[NodeReservation]:
        response = self._get(
            f"/dedicated-node-groups/{self._to_name(name_or_ng)}/reservations"
        )
        return self.ensure_list(response, NodeReservation)

    def list_storage_data_sources(
        self, name_or_ng: Union[str, DedicatedNodeGroup]
    ) -> List[StorageDataSource]:
        response = self._get(
            f"/dedicated-node-groups/{self._to_name(name_or_ng)}/datasources"
        )
        return self.ensure_list(response, StorageDataSource, list_key="items")

    def get_storage_data_source(
        self,
        name_or_ng: Union[str, DedicatedNodeGroup],
        data_source_name: str,
    ) -> StorageDataSource:
        response = self._get(
            f"/dedicated-node-groups/{self._to_name(name_or_ng)}/datasources/"
            f"{quote(data_source_name, safe='')}"
        )
        return self.ensure_type(response, StorageDataSource)

    def create_storage_data_source(
        self,
        node_group: Union[str, DedicatedNodeGroup],
        spec: StorageDataSourceSpec,
    ) -> StorageDataSource:
        response = self._post(
            f"/dedicated-node-groups/{self._to_name(node_group)}/datasources",
            json=self.safe_json(spec),
        )
        return self.ensure_type(response, StorageDataSource)

    def list_storage_permissions(
        self,
        node_group: Union[str, DedicatedNodeGroup],
        volume_name: str,
    ) -> List[StoragePermission]:
        response = self._get(
            f"/storage-permission/{quote(volume_name, safe='')}",
            params={"nodegroup_id": self._to_name(node_group)},
        )
        return self.ensure_list(response, StoragePermission)

    def set_storage_permission(
        self,
        node_group: Union[str, DedicatedNodeGroup],
        volume_name: str,
        permission: StoragePermission,
    ) -> bool:
        payload = self.safe_json(permission)
        if not isinstance(payload, dict):
            raise TypeError("Storage permission payload must be an object.")
        payload["nodegroup_id"] = self._to_name(node_group)
        response = self._post(
            f"/storage-permission/{quote(volume_name, safe='')}",
            json=payload,
        )
        return self.ensure_ok(response)

    def delete_storage_permission(
        self,
        node_group: Union[str, DedicatedNodeGroup],
        volume_name: str,
        path_prefix: str,
    ) -> bool:
        if not path_prefix.startswith("/"):
            path_prefix = "/" + path_prefix
        response = self._delete(
            f"/storage-permission/{quote(volume_name, safe='')}"
            f"{quote(path_prefix, safe='/')}",
            params={"nodegroup_id": self._to_name(node_group)},
        )
        return self.ensure_ok(response)

    def update_storage_data_source(
        self,
        node_group: Union[str, DedicatedNodeGroup],
        data_source_name: str,
        spec: StorageDataSourceSpec,
    ) -> StorageDataSource:
        response = self._patch(
            f"/dedicated-node-groups/{self._to_name(node_group)}/datasources/"
            f"{quote(data_source_name, safe='')}",
            json=self.safe_json(spec),
        )
        return self.ensure_type(response, StorageDataSource)

    def delete_storage_data_source(
        self,
        node_group: Union[str, DedicatedNodeGroup],
        data_source_name: str,
    ) -> bool:
        response = self._delete(
            f"/dedicated-node-groups/{self._to_name(node_group)}/datasources/"
            f"{quote(data_source_name, safe='')}"
        )
        return self.ensure_ok(response)

    def add_volume(
        self,
        node_group: Union[str, DedicatedNodeGroup],
        volume: Volume,
    ) -> DedicatedNodeGroup:
        response = self._post(
            f"/dedicated-node-groups/{self._to_name(node_group)}/volumes",
            json=self.safe_json(volume),
        )
        return self.ensure_type(response, DedicatedNodeGroup)

    def delete_volume(
        self,
        node_group: Union[str, DedicatedNodeGroup],
        volume_name: str,
    ) -> DedicatedNodeGroup:
        response = self._delete(
            f"/dedicated-node-groups/{self._to_name(node_group)}/volumes/"
            f"{quote(volume_name, safe='')}"
        )
        return self.ensure_type(response, DedicatedNodeGroup)

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
