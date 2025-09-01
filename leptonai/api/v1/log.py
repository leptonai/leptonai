from typing import Union

from leptonai.api.v1.api_resource import APIResourse
from leptonai.api.v1.types.deployment import LeptonDeployment
from leptonai.api.v1.types.job import LeptonJob
from leptonai.api.v1.types.replica import Replica


class LogAPI(APIResourse):
    def get_log(
        self,
        name_or_deployment: Union[str, LeptonDeployment] = None,
        name_or_job: Union[str, LeptonJob] = None,
        replica: Union[str, Replica] = None,
        job_history_name: str = None,
        start: str = None,
        end: str = None,
        limit: int = 5000,
        q: str = "",
    ) -> str:
        query_kwargs = {}
        if start and end:
            query_kwargs["start"] = start
            query_kwargs["end"] = end
            query_kwargs["timestamps"] = True
            query_kwargs["direction"] = "backward"
            query_kwargs["limit"] = limit
            query_kwargs["q"] = q
        elif start or end:
            raise RuntimeError(
                "For historical logs, both start or end must be specified"
            )

        if name_or_deployment:
            deployment_id = (
                name_or_deployment
                if isinstance(name_or_deployment, str)
                else name_or_deployment.metadata.id_
            )
            query_kwargs["deployment"] = deployment_id

        elif name_or_job:
            job_id = (
                name_or_job
                if isinstance(name_or_job, str)
                else name_or_job.metadata.id_
            )

            query_kwargs["job"] = job_id

        elif job_history_name:
            query_kwargs["job_history_name"] = job_history_name

        if replica:
            replica_id = replica if isinstance(replica, str) else replica.metadata.id_
            query_kwargs["replica"] = replica_id

        response = self._get(
            "/logs",
            params=query_kwargs,
        )
        if not response.ok:
            raise RuntimeError(
                f"API call failed with status code {response.status_code}. Details:"
                f" {response.text}"
            )
        return response.json()
