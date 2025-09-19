from typing import Union, List, Dict, Any

from .api_resource import APIResourse
from .types.raycluster import LeptonRayCluster


class RayClusterAPI(APIResourse):
    def _validate_update_spec_only_min_replicas(
        self, update_payload: Dict[str, Any]
    ) -> None:
        """
        For now, only allow updating the minimum number of replicas for worker groups,
        and require the update payload to be nested under a top-level 'spec' key so it
        is merge-patchable with the existing RayCluster.

        Allowed update payloads (top-level):
        - { "spec": { "worker_group_specs": [ { "group_name"?, "min_replicas" }, ... ] } }

        Any other fields present in the update payload will raise a ValueError.
        """
        # Require only top-level 'spec'
        unexpected_top_level = set(update_payload.keys()) - {"spec"}
        if unexpected_top_level:
            raise ValueError(
                "Only updating via top-level 'spec' is supported. Unexpected fields in"
                " payload: "
                + ", ".join(sorted(unexpected_top_level))
            )
        if "spec" not in update_payload or not isinstance(update_payload["spec"], dict):
            raise ValueError("Update payload must include top-level 'spec' object.")

        spec_obj = update_payload["spec"]

        # Only allow worker_group_specs inside spec for now
        allowed_spec_level = {"worker_group_specs"}
        unexpected_spec_level = set(spec_obj.keys()) - allowed_spec_level
        if unexpected_spec_level:
            raise ValueError(
                "Only updating worker_group_specs.min_replicas is supported. Unexpected"
                " fields in spec: "
                + ", ".join(sorted(unexpected_spec_level))
            )

        if "worker_group_specs" not in spec_obj:
            raise ValueError("spec.worker_group_specs is required and must be a list")
        if not isinstance(spec_obj["worker_group_specs"], list):
            raise ValueError("spec.worker_group_specs must be a list of group specs")
        if len(spec_obj["worker_group_specs"]) != 1:
            raise ValueError(
                "spec.worker_group_specs must contain exactly one group to update"
            )
        for idx, wg in enumerate(spec_obj["worker_group_specs"]):
            if not isinstance(wg, dict):
                raise ValueError(
                    f"spec.worker_group_specs[{idx}] must be an object with"
                    " min_replicas"
                )
            unexpected_wg = set(wg.keys()) - {"group_name", "min_replicas"}
            if unexpected_wg:
                raise ValueError(
                    f"spec.worker_group_specs[{idx}] may only include group_name and"
                    " min_replicas. Unexpected fields:"
                    f" {', '.join(sorted(unexpected_wg))}"
                )
            if "min_replicas" not in wg:
                raise ValueError(
                    f"spec.worker_group_specs[{idx}].min_replicas is required"
                )
            if not isinstance(wg["min_replicas"], int):
                raise ValueError(
                    f"spec.worker_group_specs[{idx}].min_replicas must be an integer"
                )
            if wg["min_replicas"] <= 0:
                raise ValueError(
                    f"spec.worker_group_specs[{idx}].min_replicas must be a positive"
                    " integer"
                )

            if "group_name" not in wg:
                raise ValueError(
                    f"spec.worker_group_specs[{idx}].group_name is required"
                )
            if wg["group_name"] is not None and not isinstance(wg["group_name"], str):
                raise ValueError(
                    f"spec.worker_group_specs[{idx}].group_name must be a string"
                )

    def _to_name(self, name_or_raycluster: Union[str, LeptonRayCluster]) -> str:
        return (
            name_or_raycluster
            if isinstance(name_or_raycluster, str)
            else name_or_raycluster.metadata.id_  # type: ignore[attr-defined]
        )

    def list_all(self) -> List[LeptonRayCluster]:
        response = self._get("/rayclusters")
        return self.ensure_list(response, LeptonRayCluster)

    def create(self, spec: LeptonRayCluster) -> bool:
        response = self._post("/rayclusters", json=self.safe_json(spec))
        return self.ensure_ok(response)

    def get(self, name_or_raycluster: Union[str, LeptonRayCluster]) -> LeptonRayCluster:
        response = self._get(f"/rayclusters/{self._to_name(name_or_raycluster)}")
        return self.ensure_type(response, LeptonRayCluster)

    def update(
        self,
        name_or_raycluster: Union[str, LeptonRayCluster],
        spec: LeptonRayCluster,
    ) -> LeptonRayCluster:

        if spec.spec is None:
            raise ValueError("LeptonRayCluster.spec must not be None for update.")

        payload = self.safe_json(spec)

        self._validate_update_spec_only_min_replicas(payload)

        response = self._patch(
            f"/rayclusters/{self._to_name(name_or_raycluster)}", json=payload
        )
        return self.ensure_type(response, LeptonRayCluster)

    def delete(self, name_or_raycluster: Union[str, LeptonRayCluster]) -> bool:
        response = self._delete(f"/rayclusters/{self._to_name(name_or_raycluster)}")
        return self.ensure_ok(response)
