from typing import Union, List, Optional

from ..v1.api_resource import APIResourse
from leptonai.api.v1.types.job import LeptonJobQueryMode
from .types.finetune import (
    LeptonFineTuneJob,
    FineTuneModelInfo,
    TrainerInfo,
)


class FineTuneAPI(APIResourse):
    def _to_id(self, name_or_job: Union[str, LeptonFineTuneJob]) -> str:
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
    ) -> List[LeptonFineTuneJob]:
        """
        List fine-tune jobs with optional server-side filtering.
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
            response = self._get("/finetune/jobs", params=params_base)
            return self.ensure_list(
                response, LeptonFineTuneJob, list_key="finetune_jobs"
            )

        # Otherwise auto-paginate until empty result set
        results: List[LeptonFineTuneJob] = []
        current_page = 1
        while True:
            params = dict(params_base)
            params["page"] = current_page
            params["page_size"] = 500
            response = self._get("/finetune/jobs", params=params)
            items = self.ensure_list(
                response, LeptonFineTuneJob, list_key="finetune_jobs"
            )
            if not items:
                break
            results.extend(items)
            current_page += 1
        return results

    def create(self, spec: LeptonFineTuneJob) -> LeptonFineTuneJob:
        response = self._post("/finetune/jobs", json=self.safe_json(spec))
        return self.ensure_type(response, LeptonFineTuneJob)

    def get(
        self,
        id_or_job: Union[str, LeptonFineTuneJob],
        *,
        job_query_mode: str = LeptonJobQueryMode.AliveOnly.value,
    ) -> LeptonFineTuneJob:
        response = self._get(
            f"/finetune/jobs/{self._to_id(id_or_job)}",
            params={"job_query_mode": job_query_mode} if job_query_mode else None,
        )
        return self.ensure_type(response, LeptonFineTuneJob)

    def update(
        self, name_or_job: Union[str, LeptonFineTuneJob], spec: LeptonFineTuneJob
    ) -> bool:
        response = self._patch(
            f"/finetune/jobs/{self._to_id(name_or_job)}", json=self.safe_json(spec)
        )
        return self.ensure_ok(response)

    def delete(
        self,
        name_or_job: Union[str, LeptonFineTuneJob],
        *,
        job_query_mode: str = LeptonJobQueryMode.AliveOnly.value,
    ) -> bool:
        response = self._delete(
            f"/finetune/jobs/{self._to_id(name_or_job)}",
            params={"job_query_mode": job_query_mode} if job_query_mode else None,
        )
        return self.ensure_ok(response)

    def list_supported_models(self) -> List[FineTuneModelInfo]:
        response = self._get("/finetune/supported-models")
        return self.ensure_list(response, FineTuneModelInfo)

    def list_trainers(self, default_only: bool = True) -> List[TrainerInfo]:
        response = self._get(
            "/finetune/trainers", params={"default_only": str(default_only).lower()}
        )
        return self.ensure_list(response, TrainerInfo)
