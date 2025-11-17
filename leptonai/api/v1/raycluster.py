from typing import Union, List, Dict, Any

from .api_resource import APIResourse
from .types.raycluster import LeptonRayCluster


class RayClusterAPI(APIResourse):
    def _validate_update_spec_only_min_replicas(
        self, update_payload: Dict[str, Any]
    ) -> None:
        """
        Allow updating the minimum/maximum number of replicas for worker groups and the
        suspend flag, and require the update payload to be nested under a top-level 'spec'
        key so it is merge-patchable with the existing RayCluster.

        Allowed update payloads (top-level):
        - {
            "spec": {
              "worker_group_specs": [
                 { "group_name"?, "min_replicas", "max_replicas"?, ... },
                 ...
              ]?,
              "suspend"?: bool
            }
          }

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

        # Only allow worker_group_specs and/or suspend inside spec for now
        allowed_spec_level = {"worker_group_specs", "suspend"}
        unexpected_spec_level = set(spec_obj.keys()) - allowed_spec_level
        if unexpected_spec_level:
            raise ValueError(
                "Only updating worker_group_specs.(min_replicas,max_replicas) and"
                " 'suspend' is supported. Unexpected fields in spec: "
                + ", ".join(sorted(unexpected_spec_level))
            )

        # At least one of worker_group_specs or suspend must be present
        if "worker_group_specs" not in spec_obj and "suspend" not in spec_obj:
            raise ValueError(
                "spec must include at least one of 'worker_group_specs' or 'suspend'"
            )

        # Validate suspend if provided
        if "suspend" in spec_obj:
            if not isinstance(spec_obj["suspend"], bool):
                raise ValueError("spec.suspend must be a boolean value")

        # Validate worker_group_specs if provided
        if "worker_group_specs" in spec_obj:
            if not isinstance(spec_obj["worker_group_specs"], list):
                raise ValueError(
                    "spec.worker_group_specs must be a list of group specs"
                )
            if len(spec_obj["worker_group_specs"]) == 0:
                raise ValueError(
                    "spec.worker_group_specs must contain at least one group to update"
                )
            for idx, wg in enumerate(spec_obj["worker_group_specs"]):
                if not isinstance(wg, dict):
                    raise ValueError(
                        f"spec.worker_group_specs[{idx}] must be an object with"
                        " min_replicas (and optional max_replicas)"
                    )
                unexpected_wg = set(wg.keys()) - {
                    "group_name",
                    "min_replicas",
                    "max_replicas",
                }
                if unexpected_wg:
                    raise ValueError(
                        f"spec.worker_group_specs[{idx}] may only include group_name, "
                        "min_replicas and max_replicas. Unexpected fields:"
                        f" {', '.join(sorted(unexpected_wg))}"
                    )
                if "min_replicas" not in wg:
                    raise ValueError(
                        f"spec.worker_group_specs[{idx}].min_replicas is required"
                    )
                if not isinstance(wg["min_replicas"], int):
                    raise ValueError(
                        f"spec.worker_group_specs[{idx}].min_replicas must be an"
                        " integer"
                    )
                if wg["min_replicas"] < 0:
                    raise ValueError(
                        f"spec.worker_group_specs[{idx}].min_replicas must be a"
                        " non-negative integer"
                    )

                if "max_replicas" in wg and wg["max_replicas"] is not None:
                    if not isinstance(wg["max_replicas"], int):
                        raise ValueError(
                            f"spec.worker_group_specs[{idx}].max_replicas must be an"
                            " integer"
                        )
                    if wg["max_replicas"] <= 0:
                        raise ValueError(
                            f"spec.worker_group_specs[{idx}].max_replicas must be a"
                            " positive integer"
                        )

                if "group_name" not in wg:
                    raise ValueError(
                        f"spec.worker_group_specs[{idx}].group_name is required"
                    )
                if wg["group_name"] is not None and not isinstance(
                    wg["group_name"], str
                ):
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
