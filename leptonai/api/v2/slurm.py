"""High-level API for workspace Slurm resources.

This module owns Slurm's composite identifiers, transport paths, query
parameters, and dashboard routes.  Callers should not need to know that a
cluster ID is split across two backend path segments or that log data is served
by the shared Loki-compatible endpoint.
"""

from typing import Any, List, Optional, Tuple, Union
from urllib.parse import quote

from .api_resource import APIResourse
from .types.slurm import (
    LeptonSlurmCluster,
    LeptonSlurmDevPod,
    SlurmClusterEvent,
    SlurmDevPodSpec,
    SlurmJob,
    SlurmJobEventList,
    SlurmResourceList,
    WorkspaceSlurmJobList,
)


SLURM_JOB_QUERY_MODES = (
    "alive_only",
    "archive_only",
    "alive_and_archive",
)


class SlurmAPI(APIResourse):
    """Workspace-scoped Slurm clusters, jobs, logs, and dev pods."""

    @staticmethod
    def split_cluster_id(cluster_id: str) -> Tuple[str, str]:
        """Split and validate a canonical ``namespace/name`` cluster ID."""
        value = str(cluster_id).strip()
        parts = value.split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError(
                "Slurm cluster ID must be in the form 'namespace/name'; got "
                f"{cluster_id!r}."
            )
        return parts[0], parts[1]

    @classmethod
    def _cluster_path(cls, cluster_id: str) -> str:
        namespace, name = cls.split_cluster_id(cluster_id)
        return f"{quote(namespace, safe='')}/{quote(name, safe='')}"

    @classmethod
    def _cluster_name(cls, cluster_id_or_name: str) -> str:
        value = str(cluster_id_or_name).strip()
        if "/" in value:
            return cls.split_cluster_id(value)[1]
        if not value:
            raise ValueError("Slurm cluster name cannot be empty.")
        return value

    def list_clusters(self) -> List[LeptonSlurmCluster]:
        response = self._get("/slurmclusters")
        return self.ensure_list(response, LeptonSlurmCluster)

    def get_cluster(self, cluster_id: str) -> LeptonSlurmCluster:
        # There is deliberately no resource GET route.  Keep that detail here
        # so CLI commands and SDK callers share exact matching semantics.
        self.split_cluster_id(cluster_id)
        for cluster in self.list_clusters():
            if cluster.metadata.id_ == cluster_id:
                return cluster
        raise ValueError(f"Slurm cluster {cluster_id!r} was not found.")

    def list_cluster_events(
        self,
        cluster_id: str,
        *,
        limit: int = 100,
        event_type: Optional[str] = None,
    ) -> List[SlurmClusterEvent]:
        params = {"limit": limit}
        if event_type:
            params["event_type"] = event_type
        response = self._get(
            f"/slurmclusters/{self._cluster_path(cluster_id)}/history", params=params
        )
        return self.ensure_list(response, SlurmClusterEvent)

    def list_jobs(
        self,
        *,
        cluster_names: Optional[List[str]] = None,
        job_query_mode: str = "alive_only",
        q: Optional[str] = None,
        status: Optional[List[str]] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        created_by: Optional[List[str]] = None,
        partition: Optional[List[str]] = None,
        qos: Optional[List[str]] = None,
        sort_fields: Optional[str] = None,
        sort_orders: Optional[str] = None,
    ) -> WorkspaceSlurmJobList:
        if job_query_mode not in SLURM_JOB_QUERY_MODES:
            raise ValueError(
                "Invalid Slurm job query mode. Expected one of: "
                + ", ".join(SLURM_JOB_QUERY_MODES)
            )

        params: Any = {"job_query_mode": job_query_mode}
        if cluster_names:
            params["cluster_name"] = [self._cluster_name(v) for v in cluster_names]
        if q:
            params["q"] = q
        if status:
            params["status"] = status
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if created_by:
            params["created_by"] = created_by
        if partition:
            params["partition"] = partition
        if qos:
            params["qos"] = qos
        if sort_fields:
            params["sort_fields"] = sort_fields
        if sort_orders:
            params["sort_orders"] = sort_orders

        response = self._get("/slurm/jobs", params=params)
        return self.ensure_type(response, WorkspaceSlurmJobList)

    def get_job(
        self, cluster_id: str, job_id: Union[str, int], *, slurm_api: bool = False
    ) -> Union[SlurmJob, Any]:
        response = self._get(
            f"/slurmclusters/{self._cluster_path(cluster_id)}/jobs/"
            f"{quote(str(job_id), safe='')}",
            params={"slurm_api": "true"} if slurm_api else None,
        )
        if slurm_api:
            return self.ensure_json(response)
        return self.ensure_type(response, SlurmJob)

    def get_job_events(
        self, cluster_id: str, job_id: Union[str, int]
    ) -> SlurmJobEventList:
        response = self._get(
            f"/slurmclusters/{self._cluster_path(cluster_id)}/jobs/"
            f"{quote(str(job_id), safe='')}/events"
        )
        return self.ensure_type(response, SlurmJobEventList)

    def get_logs(
        self,
        cluster_id: str,
        *,
        job_id: Optional[Union[str, int]] = None,
        attempt: Optional[int] = None,
        step: Optional[str] = None,
        node: Optional[str] = None,
        log_type: Optional[str] = None,
        query: Optional[str] = None,
        start: Optional[int] = None,
        end: Optional[int] = None,
        limit: int = 100,
        direction: str = "backward",
    ) -> Any:
        namespace, name = self.split_cluster_id(cluster_id)
        if direction not in ("forward", "backward"):
            raise ValueError("Log direction must be 'forward' or 'backward'.")
        params: Any = {
            "slurm_namespace": namespace,
            "slurm_cluster": name,
            "limit": limit,
            "direction": direction,
        }
        optional = {
            "slurm_job": None if job_id is None else str(job_id),
            "slurm_attempt": attempt,
            "slurm_step": step,
            "slurm_node": node,
            "slurm_log_type": log_type,
            "q": query,
            "start": start,
            "end": end,
        }
        params.update(
            {key: value for key, value in optional.items() if value is not None}
        )
        response = self._get("/logs", params=params)
        return self.ensure_json(response)

    def list_devpods(
        self, *, cluster_names: Optional[List[str]] = None
    ) -> List[LeptonSlurmDevPod]:
        params = None
        if cluster_names:
            params = {"cluster_name": [self._cluster_name(v) for v in cluster_names]}
        response = self._get("/slurm/devpods", params=params)
        return self.ensure_list(response, LeptonSlurmDevPod)

    def get_devpod(self, devpod_id: str) -> LeptonSlurmDevPod:
        response = self._get(f"/slurm/devpods/{self._cluster_path(devpod_id)}")
        return self.ensure_type(response, LeptonSlurmDevPod)

    def resolve_devpod(self, target: str) -> LeptonSlurmDevPod:
        """Resolve a dev pod ID/name or a canonical Slurm cluster ID."""
        value = str(target).strip()
        if not value:
            raise ValueError("Slurm dev pod target cannot be empty.")
        pods = self.list_devpods()

        exact = [pod for pod in pods if value in (pod.metadata.id_, pod.metadata.name)]
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            raise ValueError(f"Slurm dev pod target {target!r} is ambiguous.")

        namespace = None
        cluster_name = value
        if "/" in value:
            namespace, cluster_name = self.split_cluster_id(value)
        cluster_matches = []
        for pod in pods:
            if pod.spec.slurm_cluster_name != cluster_name:
                continue
            if namespace is not None:
                pod_namespace = (pod.metadata.id_ or "").split("/", 1)[0]
                if pod_namespace != namespace:
                    continue
            cluster_matches.append(pod)

        if len(cluster_matches) == 1:
            return cluster_matches[0]
        if not cluster_matches:
            raise ValueError(
                f"No Slurm dev pod found for ID, name, or cluster {target!r}."
            )
        raise ValueError(
            f"Multiple Slurm dev pods match {target!r}; use the canonical dev pod ID."
        )

    def create_devpod(
        self,
        cluster_id: str,
        *,
        set_name: Optional[str] = None,
        cpu: Optional[str] = None,
        memory: Optional[str] = None,
    ) -> LeptonSlurmDevPod:
        cluster_name = self._cluster_name(cluster_id)
        requests = None
        if cpu is not None or memory is not None:
            requests = SlurmResourceList(cpu=cpu, memory=memory)
        spec = SlurmDevPodSpec(
            slurmClusterName=cluster_name,
            devPodSetName=set_name,
            resourceRequests=requests,
        )
        spec_json = (
            spec.model_dump(by_alias=True, exclude_none=True)
            if hasattr(spec, "model_dump")
            else self.safe_json(spec)
        )
        response = self._post("/slurm/devpods", json={"spec": spec_json})
        return self.ensure_type(response, LeptonSlurmDevPod)

    def delete_devpod(self, devpod_id: str) -> bool:
        response = self._delete(f"/slurm/devpods/{self._cluster_path(devpod_id)}")
        return self.ensure_ok(response)

    def dashboard_url(
        self,
        view: str = "clusters",
        *,
        cluster_id: Optional[str] = None,
        job_id: Optional[Union[str, int]] = None,
    ) -> str:
        """Build a canonical dashboard URL for a Slurm resource or view."""
        base = self._client.get_dashboard_base_url()
        if not base:
            raise ValueError(
                "Could not determine the dashboard URL for this workspace."
            )
        base = base.rstrip("/")

        if cluster_id is None:
            if job_id is not None:
                raise ValueError("A cluster ID is required for a Slurm job URL.")
            if view in ("clusters", "cluster", "list"):
                return f"{base}/clusters/slurm/list"
            if view in ("jobs", "job-list"):
                return f"{base}/compute/jobs/slurm-list"
            raise ValueError(f"Unsupported workspace Slurm dashboard view: {view!r}.")

        self.split_cluster_id(cluster_id)
        cluster = quote(cluster_id, safe="")
        cluster_base = f"{base}/clusters/slurm/detail/{cluster}"

        if job_id is None:
            cluster_views = {
                "detail": "",
                "overview": "",
                "jobs": "/jobs/list",
                "archived-jobs": "/jobs/archived-list",
                "events": "/events",
                "metrics": "/metrics",
                "devpods": "/dev-pods",
                "dev-pods": "/dev-pods",
            }
            if view == "logs":
                return f"{base}#/slurm-cluster/{cluster}/logs"
            if view not in cluster_views:
                raise ValueError(f"Unsupported Slurm cluster dashboard view: {view!r}.")
            return cluster_base + cluster_views[view]

        job = quote(str(job_id), safe="")
        job_base = f"{cluster_base}/jobs/detail/{job}"
        if view in ("detail", "overview"):
            return f"{job_base}/overview"
        if view == "attempts":
            return f"{job_base}/attempts"
        if view in ("metrics", "logs"):
            return f"{base}#/slurm-cluster/{cluster}/jobs/{job}/{view}"
        raise ValueError(f"Unsupported Slurm job dashboard view: {view!r}.")
