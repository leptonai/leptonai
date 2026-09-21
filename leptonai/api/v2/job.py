from typing import Union, List, Iterator, Optional
from urllib.parse import quote

from .api_resource import APIResourse
from .job_validation import validate_job_create
from .types.events import LeptonEvent

from .types.job import LeptonJob, LeptonJobQueryMode
from .types.replica import Replica


class JobAPI(APIResourse):
    def _to_id(self, name_or_job: Union[str, LeptonJob]) -> str:
        return (  # type: ignore
            name_or_job if isinstance(name_or_job, str) else name_or_job.metadata.id_
        )

    def list_all(
        self,
        *,
        job_query_mode: str = LeptonJobQueryMode.AliveOnly.value,
        q: Optional[str] = None,
        query: Optional[str] = None,
        status: Optional[List[str]] = None,
        node_groups: Optional[List[str]] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        created_by: Optional[str] = None,
    ) -> List[LeptonJob]:
        """List jobs with optional server-side filtering.

        Mirrors backend query parameters (see OpenAPI docs):
        - job_query_mode: alive_only | archive_only | alive_and_archive
        - q           : substring match for job name
        - query       : label selector
        - status      : list of job states
        - page / page_size: pagination controls
        - created_by  : creator email (single)
        """
        params_base = {"job_query_mode": job_query_mode}
        if q:
            params_base["q"] = q
        if query:
            params_base["query"] = query
        if status:
            params_base["status"] = status
        if node_groups:
            params_base["node_groups"] = node_groups
        if created_by:
            params_base["created_by"] = created_by

        # If user explicitly specifies page or page_size, do single request
        if page is not None or page_size is not None:
            if page is not None:
                params_base["page"] = page
            if page_size is not None:
                params_base["page_size"] = page_size
            response = self._get("/jobs", params=params_base)
            return self.ensure_list(response, LeptonJob, list_key="jobs")

        # Otherwise auto-paginate until empty result set
        results: List[LeptonJob] = []
        current_page = 1
        while True:
            params = dict(params_base)
            params["page"] = current_page
            params["page_size"] = 500
            response = self._get("/jobs", params=params)
            items = self.ensure_list(response, LeptonJob, list_key="jobs")
            if not items:
                break
            results.extend(items)
            current_page += 1
        return results

    def list_matching(self, pattern: str):
        params = {
            "query": pattern,
        }
        responses = self._get("/jobs", params=params)
        return self.ensure_list(responses, LeptonJob)

    def create(self, spec: LeptonJob) -> LeptonJob:
        """
        Create a job with the given job spec.
        """
        validate_job_create(spec)
        response = self._post("/jobs", json=self.safe_json(spec))
        return self.ensure_type(response, LeptonJob)

    def get(
        self,
        id_or_job: Union[str, LeptonJob],
        *,
        job_query_mode: str = LeptonJobQueryMode.AliveAndArchive.value,
    ) -> LeptonJob:
        response = self._get(
            f"/jobs/{self._to_id(id_or_job)}",
            params={"job_query_mode": job_query_mode} if job_query_mode else None,
        )
        return self.ensure_type(response, LeptonJob)

    def update(self, name_or_job: Union[str, LeptonJob], spec: LeptonJob) -> bool:
        response = self._patch(f"/jobs/{self._to_id(name_or_job)}", json=spec)
        return self.ensure_ok(response)

    def delete(
        self,
        name_or_job: Union[str, LeptonJob],
        *,
        job_query_mode: str = LeptonJobQueryMode.AliveOnly.value,
    ) -> bool:
        response = self._delete(
            f"/jobs/{self._to_id(name_or_job)}",
            params={"job_query_mode": job_query_mode} if job_query_mode else None,
        )
        return self.ensure_ok(response)

    def get_events(self, name_or_job: Union[str, LeptonJob]) -> List[LeptonEvent]:
        response = self._get(f"/jobs/{self._to_id(name_or_job)}/events")
        return self.ensure_list(response, LeptonEvent)

    def get_replicas(
        self,
        name_or_job: Union[str, LeptonJob],
        job_query_mode: str = "alive_and_archive",
    ) -> List[Replica]:
        response = self._get(
            f"/jobs/{self._to_id(name_or_job)}/replicas",
            params={"job_query_mode": job_query_mode},
        )
        return self.ensure_list(response, Replica)

    def get_ssh_replica(
        self, id_or_job: Union[str, LeptonJob], replica: Optional[str] = None
    ) -> str:
        """Select one live Job replica without guessing among workers or history."""
        job = self.get(id_or_job, job_query_mode=LeptonJobQueryMode.AliveOnly.value)
        if job.status is None or job.status.state != "Running":
            raise RuntimeError("SSH requires a running job.")
        job_id = self._to_id(job)
        if not job_id:
            raise RuntimeError("The job response is missing its ID.")
        replicas = self.ensure_json(
            self._get(
                f"/jobs/{quote(job_id, safe='')}/replicas",
                params={"job_query_mode": LeptonJobQueryMode.AliveOnly.value},
            )
        )
        if not isinstance(replicas, list):
            raise RuntimeError("The server returned an invalid job replica list.")
        ids = []
        ready_ids = []
        for item in replicas:
            metadata = item.get("metadata") if isinstance(item, dict) else None
            rid = metadata.get("id") if isinstance(metadata, dict) else None
            if not isinstance(rid, str) or not rid.strip() or rid in ids:
                raise RuntimeError(
                    "The server returned invalid or duplicate job replica IDs."
                )
            ids.append(rid)
            status = item.get("status")
            readiness = (
                status.get("readiness_issue") if isinstance(status, dict) else None
            )
            if isinstance(readiness, dict) and readiness.get("reason") == "Ready":
                ready_ids.append(rid)
        if replica is not None:
            if replica not in ids:
                raise RuntimeError(
                    "The requested replica does not belong to the current job run. "
                    f"List current replicas with: lep job replicas --id {job_id}"
                )
            if replica not in ready_ids:
                raise RuntimeError("The selected Job replica is not ready for SSH.")
            return replica
        if not ready_ids:
            raise RuntimeError("The job has no ready replicas available for SSH.")
        if len(ready_ids) != 1:
            raise RuntimeError(
                "The job has multiple replicas. Select one with --replica. "
                f"List current replicas with: lep job replicas --id {job_id}"
            )
        return ready_ids[0]

    def get_log(
        self,
        id_or_job: Union[str, LeptonJob],
        replica: Union[str, Replica],
        timeout: Optional[int] = None,
    ) -> Iterator[str]:
        """
        Gets the log of the given job's specified replica. The log is streamed
        in chunks until timeout is reached. If timeout is not specified, the log will be
        streamed indefinitely, although you should not rely on this behavior as connections
        can be dropped when streamed for a long time.
        """
        replica_id = replica if isinstance(replica, str) else replica.metadata.id_
        response = self._get(
            f"/jobs/{self._to_id(id_or_job)}/replicas/{replica_id}/log",
            stream=True,
            timeout=timeout,
        )
        if not response.ok:
            raise RuntimeError(
                f"API call failed with status code {response.status_code}. Details:"
                f" {response.text}"
            )
        for chunk in response.iter_content(chunk_size=None):
            if chunk:
                yield chunk.decode("utf8")
