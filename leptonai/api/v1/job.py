from typing import Union

from .common import APIResourse

from .types.job import LeptonJob


class JobAPI(APIResourse):
    def list_all(self):
        responses = self._get("/jobs")
        return self._ws.ensure_list(responses, LeptonJob)

    def create(self, spec: LeptonJob) -> LeptonJob:
        """
        Run a photon with the given job spec.
        """
        response = self._post("/jobs", json=spec.dict(exclude_none=True))
        return self._ws.ensure_type(response, LeptonJob)

    def get(self, name_or_job: Union[str, LeptonJob]) -> LeptonJob:
        name = name_or_job if isinstance(name_or_job, str) else name_or_job.metadata.id
        response = self._get(f"/jobs/{name}")
        return self._ws.ensure_type(response, LeptonJob)

    def update(self, name_or_job: Union[str, LeptonJob], spec: LeptonJob) -> bool:
        raise NotImplementedError("Job update is not implemented yet.")

    def delete(self, name_or_job: Union[str, LeptonJob]) -> bool:
        name = name_or_job if isinstance(name_or_job, str) else name_or_job.metadata.id
        response = self._delete(f"/jobs/{name}")
        return self._ws.ensure_ok(response)
