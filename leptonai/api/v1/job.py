from typing import Union, List, Iterator, Optional

from .api_resource import APIResourse
from .types.events import LeptonEvent

from .types.job import LeptonJob
from .types.replica import Replica


class JobAPI(APIResourse):
    def _to_id(self, name_or_job: Union[str, LeptonJob]) -> str:
        return (  # type: ignore
            name_or_job if isinstance(name_or_job, str) else name_or_job.metadata.id_
        )

    def list_all(
        self,
        *,
        job_query_mode: str = "alive_only",
        q: Optional[str] = None,
        query: Optional[str] = None,
        status: Optional[List[str]] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        created_by: Optional[List[str]] = None,
    ) -> List[LeptonJob]:
        """List jobs with optional server-side filtering.

        Mirrors backend query parameters (see OpenAPI docs):
        - job_query_mode: alive_only | archive_only | alive_and_archive
        - q           : substring match for job name
        - query       : label selector
        - status      : list of job states
        - page / page_size: pagination controls
        - created_by  : list of creator emails
        """
        params_base = {"job_query_mode": job_query_mode}
        if q:
            params_base["q"] = q
        if query:
            params_base["query"] = query
        if status:
            params_base["status"] = status
        if created_by:
            params_base["created_by"] = created_by

        # If user explicitly specifies page or page_size, do single request
        if page is not None or page_size is not None:
            if page is not None:
                params_base["page"] = page
            if page_size is not None:
                params_base["page_size"] = page_size
            response = self._get("/jobs", params=params_base)
            data = response.json()
            items_raw = data.get("jobs", data) if isinstance(data, dict) else data
            return [LeptonJob(**item) for item in items_raw]

        # Otherwise auto-paginate until empty result set
        results: List[LeptonJob] = []
        current_page = 1
        while True:
            params = dict(params_base)
            params["page"] = current_page
            params["page_size"] = 500
            response = self._get("/jobs", params=params)
            data = response.json()
            items_raw = data.get("jobs", data) if isinstance(data, dict) else data
            items = [LeptonJob(**item) for item in items_raw]
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
        Run a photon with the given job spec.
        """
        response = self._post("/jobs", json=self.safe_json(spec))
        return self.ensure_type(response, LeptonJob)

    def get(self, id_or_job: Union[str, LeptonJob]) -> LeptonJob:
        response = self._get(f"/jobs/{self._to_id(id_or_job)}")
        return self.ensure_type(response, LeptonJob)

    def update(self, name_or_job: Union[str, LeptonJob], spec: LeptonJob) -> bool:
        response = self._patch(f"/jobs/{self._to_id(name_or_job)}", json=spec)
        return self.ensure_ok(response)

    def delete(self, name_or_job: Union[str, LeptonJob]) -> bool:
        response = self._delete(f"/jobs/{self._to_id(name_or_job)}")
        return self.ensure_ok(response)

    def get_events(self, name_or_job: Union[str, LeptonJob]) -> List[LeptonEvent]:
        response = self._get(f"/jobs/{self._to_id(name_or_job)}/events")
        return self.ensure_list(response, LeptonEvent)

    def get_replicas(self, name_or_job: Union[str, LeptonJob]) -> List[Replica]:
        response = self._get(f"/jobs/{self._to_id(name_or_job)}/replicas")
        return self.ensure_list(response, Replica)

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
