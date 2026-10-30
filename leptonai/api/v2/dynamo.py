"""
DynamoGraphDeploymentAPI: the ``/dynamographdeployments`` resource.

Route coverage (verified against api-server/httpapi/dynamo/handler.go and
api-server/httpapi/metrics/handler_metrics.go):

- list / create / get / delete / update (RFC 7396 merge patch, ``?dryrun=true``)
- ``/:dgdid/services``, ``/:dgdid/services/:service``,
  ``/:dgdid/services/:service/replicas``,
  ``/:dgdid/services/:service/replicas/:rid/log``,
  ``/:dgdid/services/:service/replicas/:rid`` (DELETE),
  ``/:dgdid/services/:service/restart`` (PUT)
- flat ``/:dgdid/replicas[?service=]``, ``/:dgdid/replicas/:rid/log``,
  ``/:dgdid/replicas/:rid`` (DELETE)
- ``/:dgdid/history``, ``/:dgdid/monitoring/status``
- ``/:dgdid/monitoring/:metric[?window=H]`` and
  ``/:dgdid/replicas/:rid/monitoring/:metric``

Replica logs are one-shot JSON payloads (the handler reads the ``tail`` query
parameter, default 100 lines); they do not stream. Historical logs for a Dynamo
deployment go through :class:`leptonai.api.v2.log.LogAPI` with
``name_or_dynamo=``.
"""

from typing import Any, Dict, List, Optional, Union

from .api_resource import APIResourse
from .types.dynamo import (
    DynamoHistoryItem,
    DynamoMonitoringStatusResponse,
    DynamoReplica,
    DynamoReplicaDeleteResponse,
    DynamoReplicaLogResponse,
    DynamoServiceReplicasResponse,
    DynamoServiceResponse,
    DynamoServiceRestartResponse,
    DynamoServicesResponse,
    LeptonDynamoGraphDeployment,
)


class DynamoGraphDeploymentAPI(APIResourse):
    _BASE = "/dynamographdeployments"

    def _to_name(
        self, name_or_deployment: Union[str, LeptonDynamoGraphDeployment]
    ) -> str:
        if isinstance(name_or_deployment, str):
            return name_or_deployment
        metadata = name_or_deployment.metadata
        if metadata is None or not (metadata.id_ or metadata.name):
            raise ValueError(
                "LeptonDynamoGraphDeployment.metadata.id (or name) is required to"
                " address the deployment."
            )
        return metadata.id_ or metadata.name  # type: ignore[return-value]

    def _path(self, name_or_deployment, *segments: str) -> str:
        parts = [self._BASE, self._to_name(name_or_deployment), *segments]
        return "/".join(parts)

    # ------------------------------------------------------------------ CRUD

    def list_all(self) -> List[LeptonDynamoGraphDeployment]:
        response = self._get(self._BASE)
        return self.ensure_list(response, LeptonDynamoGraphDeployment)

    def create(self, spec: LeptonDynamoGraphDeployment) -> LeptonDynamoGraphDeployment:
        """Create a deployment and return the created (sanitized) resource."""
        response = self._post(self._BASE, json=self.safe_json(spec))
        return self.ensure_type(response, LeptonDynamoGraphDeployment)

    def get(
        self, name_or_deployment: Union[str, LeptonDynamoGraphDeployment]
    ) -> LeptonDynamoGraphDeployment:
        response = self._get(self._path(name_or_deployment))
        return self.ensure_type(response, LeptonDynamoGraphDeployment)

    def update(
        self,
        name_or_deployment: Union[str, LeptonDynamoGraphDeployment],
        patch: Dict[str, Any],
        dryrun: bool = False,
    ) -> LeptonDynamoGraphDeployment:
        """
        Apply an RFC 7396 JSON Merge Patch to the deployment.

        ``patch`` is sent as-is: ``{"spec": {"services": {"worker": None}}}``
        removes the ``worker`` service, and nested keys set to ``None`` are
        deleted server side. Use :func:`leptonai.api.v2.dynamo_patch.build_merge_patch`
        to derive a patch from two spec dicts. With ``dryrun=True`` the server
        validates the patched spec without persisting it.
        """
        if not isinstance(patch, dict):
            raise ValueError("The update patch must be a JSON object (dict).")
        params = {"dryrun": "true"} if dryrun else None
        response = self._patch(
            self._path(name_or_deployment), json=patch, params=params
        )
        return self.ensure_type(response, LeptonDynamoGraphDeployment)

    def delete(
        self, name_or_deployment: Union[str, LeptonDynamoGraphDeployment]
    ) -> bool:
        response = self._delete(self._path(name_or_deployment))
        return self.ensure_ok(response)

    # -------------------------------------------------------------- services

    def list_services(
        self, name_or_deployment: Union[str, LeptonDynamoGraphDeployment]
    ) -> DynamoServicesResponse:
        response = self._get(self._path(name_or_deployment, "services"))
        return self.ensure_type(response, DynamoServicesResponse)

    def get_service(
        self,
        name_or_deployment: Union[str, LeptonDynamoGraphDeployment],
        service: str,
    ) -> DynamoServiceResponse:
        response = self._get(self._path(name_or_deployment, "services", service))
        return self.ensure_type(response, DynamoServiceResponse)

    def restart_service(
        self,
        name_or_deployment: Union[str, LeptonDynamoGraphDeployment],
        service: str,
    ) -> DynamoServiceRestartResponse:
        """Restart a service by deleting all of its pods."""
        response = self._put(
            self._path(name_or_deployment, "services", service, "restart")
        )
        return self.ensure_type(response, DynamoServiceRestartResponse)

    # -------------------------------------------------------------- replicas

    def list_replicas(
        self,
        name_or_deployment: Union[str, LeptonDynamoGraphDeployment],
        service: Optional[str] = None,
    ) -> List[DynamoReplica]:
        """List replicas across all services, optionally filtered by service."""
        params = {"service": service} if service else None
        response = self._get(self._path(name_or_deployment, "replicas"), params=params)
        return self.ensure_list(response, DynamoReplica)

    def list_service_replicas(
        self,
        name_or_deployment: Union[str, LeptonDynamoGraphDeployment],
        service: str,
    ) -> DynamoServiceReplicasResponse:
        response = self._get(
            self._path(name_or_deployment, "services", service, "replicas")
        )
        return self.ensure_type(response, DynamoServiceReplicasResponse)

    def get_replica_log(
        self,
        name_or_deployment: Union[str, LeptonDynamoGraphDeployment],
        replica: str,
        service: Optional[str] = None,
        tail: Optional[int] = None,
        timestamps: bool = False,
    ) -> DynamoReplicaLogResponse:
        """
        Fetch the current log of one replica (pod). This is a one-shot payload,
        not a stream. ``tail`` defaults to 100 lines server side. When
        ``service`` is given the service-scoped route is used, which also
        verifies that the pod belongs to that service.
        """
        if service:
            path = self._path(
                name_or_deployment, "services", service, "replicas", replica, "log"
            )
        else:
            path = self._path(name_or_deployment, "replicas", replica, "log")
        params: Dict[str, Any] = {}
        if tail is not None:
            if tail <= 0:
                raise ValueError("tail must be a positive integer.")
            params["tail"] = tail
        if timestamps:
            params["timestamps"] = "true"
        response = self._get(path, params=params or None)
        return self.ensure_type(response, DynamoReplicaLogResponse)

    def delete_replica(
        self,
        name_or_deployment: Union[str, LeptonDynamoGraphDeployment],
        replica: str,
        service: Optional[str] = None,
    ) -> DynamoReplicaDeleteResponse:
        """Delete one replica (pod); the operator launches a replacement."""
        if service:
            path = self._path(
                name_or_deployment, "services", service, "replicas", replica
            )
        else:
            path = self._path(name_or_deployment, "replicas", replica)
        response = self._delete(path)
        return self.ensure_type(response, DynamoReplicaDeleteResponse)

    # ------------------------------------------------------------ monitoring

    def get_monitoring_status(
        self, name_or_deployment: Union[str, LeptonDynamoGraphDeployment]
    ) -> DynamoMonitoringStatusResponse:
        response = self._get(self._path(name_or_deployment, "monitoring", "status"))
        return self.ensure_type(response, DynamoMonitoringStatusResponse)

    def get_history(
        self, name_or_deployment: Union[str, LeptonDynamoGraphDeployment]
    ) -> List[DynamoHistoryItem]:
        response = self._get(self._path(name_or_deployment, "history"))
        return self.ensure_list(response, DynamoHistoryItem)

    def get_metric(
        self,
        name_or_deployment: Union[str, LeptonDynamoGraphDeployment],
        metric: str,
        window: Optional[int] = None,
    ) -> Any:
        """
        Deployment-level metric series (e.g. ``GPUUtilAvg``). ``window`` is a
        plain integer number of hours (the dashboard offers 1, 2, 3, 6, 12, 24).
        Returns the decoded JSON list of ``{"metric": {...}, "values": [...]}``.
        """
        params = {"window": window} if window is not None else None
        response = self._get(
            self._path(name_or_deployment, "monitoring", metric), params=params
        )
        return self.ensure_json(response)

    def get_replica_metric(
        self,
        name_or_deployment: Union[str, LeptonDynamoGraphDeployment],
        replica: str,
        metric: str,
    ) -> Any:
        """Replica-level metric series (e.g. ``GPUUtil``). No window parameter."""
        response = self._get(
            self._path(name_or_deployment, "replicas", replica, "monitoring", metric)
        )
        return self.ensure_json(response)
