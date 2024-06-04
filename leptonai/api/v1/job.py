from typing import Union, List

from .api_resource import APIResourse

from .types.job import LeptonJob


class JobAPI(APIResourse):
    def _to_name(self, name_or_job: Union[str, LeptonJob]) -> str:
        return (  # type: ignore
            name_or_job if isinstance(name_or_job, str) else name_or_job.metadata.id_
        )

    def list_all(self) -> List[LeptonJob]:
        responses = self._get("/jobs")
        return self.ensure_list(responses, LeptonJob)

    def create(self, spec: LeptonJob) -> LeptonJob:
        """
        Run a photon with the given job spec.
        """
        response = self._post("/jobs", json=self.safe_json(spec))
        return self.ensure_type(response, LeptonJob)

    def get(self, name_or_job: Union[str, LeptonJob]) -> LeptonJob:
        response = self._get(f"/jobs/{self._to_name(name_or_job)}")
        return self.ensure_type(response, LeptonJob)

    def update(self, name_or_job: Union[str, LeptonJob], spec: LeptonJob) -> bool:
        raise NotImplementedError("Job update is not implemented yet.")

    def delete(self, name_or_job: Union[str, LeptonJob]) -> bool:
        response = self._delete(f"/jobs/{self._to_name(name_or_job)}")
        return self.ensure_ok(response)
