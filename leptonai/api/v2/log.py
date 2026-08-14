from typing import Union

from leptonai.api.v2.api_resource import APIResourse
from leptonai.api.v2.types.deployment import LeptonDeployment
from leptonai.api.v2.types.job import LeptonJob
from leptonai.api.v2.types.replica import Replica
from leptonai.api.v2.types.job import LeptonJobQueryMode


class LogAPI(APIResourse):
    def _workload_log_param(self) -> str:
        """The query key the shared ``/logs*`` routes use for a deployment/endpoint.

        When the new deployment API is enabled the workload is a LeptonEndpoint,
        and the backend keys its logs under ``endpoint=`` (a distinct branch in
        ``api-server/httpapi/log/handler_log.go``); the legacy ``deployment=``
        key resolves a /deployments resource that does not exist in that mode, so
        the query would silently return no logs. Off, the legacy key is correct.
        """
        return "endpoint" if self._client.new_deployment_api_enabled else "deployment"

    def get_log_time_series(
        self,
        name_or_deployment: Union[str, LeptonDeployment] = None,
        name_or_job: Union[str, LeptonJob] = None,
        replica: Union[str, Replica] = None,
        start: int = None,
        end: int = None,
        interval_ms: int = None,
        limit: int = None,
        q: str = "",
        job_query_mode: str = LeptonJobQueryMode.AliveAndArchive.value,
        direction: str = "backward",
    ):
        """
        Call /logs/timeseries to retrieve aggregated time series for logs.

        Args:
            name_or_deployment: Deployment name or object
            name_or_job: Job id or object
            replica: Replica id or object
            start: Start timestamp (ns)
            end: End timestamp (ns)
            interval_ms: Bucket interval in milliseconds
            limit: Max number of data points
            q: Query string
            job_query_mode: alive_and_archive | alive_only | archive_only (backend specific)
            direction: forward | backward
        Returns:
            JSON-decoded response from the API
        """

        query_kwargs = {}

        if start is not None:
            query_kwargs["start"] = start
        if end is not None:
            query_kwargs["end"] = end
        if interval_ms is not None:
            query_kwargs["interval_ms"] = interval_ms
        if limit is not None:
            query_kwargs["limit"] = limit
        if q is not None:
            query_kwargs["q"] = q
        if job_query_mode:
            query_kwargs["job_query_mode"] = job_query_mode
        if direction:
            query_kwargs["direction"] = direction

        if name_or_deployment:
            deployment_id = (
                name_or_deployment
                if isinstance(name_or_deployment, str)
                else name_or_deployment.metadata.id_
            )
            query_kwargs[self._workload_log_param()] = deployment_id
        elif name_or_job:
            job_id = (
                name_or_job
                if isinstance(name_or_job, str)
                else name_or_job.metadata.id_
            )
            query_kwargs["job"] = job_id

        if replica:
            replica_id = replica if isinstance(replica, str) else replica.metadata.id_
            query_kwargs["replica"] = replica_id

        response = self._get(
            "/logs/timeseries",
            params=query_kwargs,
        )
        if not response.ok:
            raise RuntimeError(
                f"API call failed with status code {response.status_code}. Details:"
                f" {response.text}"
            )
        return response.json()

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
        job_query_mode: str = "alive_and_archive",
    ) -> str:
        query_kwargs = {}
        if start and end:
            query_kwargs["start"] = start
            query_kwargs["end"] = end
            query_kwargs["timestamps"] = True
            query_kwargs["direction"] = "backward"
            query_kwargs["limit"] = limit
            query_kwargs["q"] = q
            if job_query_mode:
                query_kwargs["job_query_mode"] = job_query_mode
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
            query_kwargs[self._workload_log_param()] = deployment_id

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
