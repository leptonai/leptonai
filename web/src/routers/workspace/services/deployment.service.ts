import { MetricUtilService } from "@lepton-dashboard/routers/workspace/services/metric-util.service";
import { Injectable } from "injection-js";
import { BehaviorSubject, forkJoin, map, Observable, tap } from "rxjs";
import {
  Deployment,
  Replica,
  DeploymentEvent,
  Metric,
} from "@lepton-dashboard/interfaces/deployment";
import { ApiService } from "@lepton-dashboard/routers/workspace/services/api.service";
import { Subset } from "@lepton-dashboard/interfaces/subset";
import { OpenAPIRequest } from "@lepton-libs/open-api-tool";
import { ProfileService } from "@lepton-dashboard/services/profile.service";

@Injectable()
export class DeploymentService {
  private list$ = new BehaviorSubject<Deployment[]>([]);
  list(): Observable<Deployment[]> {
    return this.list$;
  }

  listReplicas(deploymentId: string): Observable<Replica[]> {
    return this.apiService.listDeploymentReplicas(deploymentId);
  }

  listEvents(deploymentId: string): Observable<DeploymentEvent[]> {
    return this.apiService.listDeploymentEvents(deploymentId);
  }

  getReplicaLog(deploymentId: string, replicaId: string): Observable<string> {
    return this.apiService.getDeploymentReplicaLogs(deploymentId, replicaId);
  }

  getReplicaSocketUrl(
    origin: string,
    deploymentId: string,
    replicaId: string
  ): string {
    const host = new URL(origin).host;
    const url = new URL(
      this.apiService.getDeploymentReplicaSocketUrl(
        host,
        deploymentId,
        replicaId
      )
    );
    const token =
      this.profileService.profile?.authorized_workspaces?.find(
        (i) => new URL(i.auth.url).host === host
      )?.auth.token || "";

    url.searchParams.set("access_token", token);

    return url.toString();
  }
  getReplicaMetrics(
    deploymentId: string,
    replicaId: string,
    metricName: string[]
  ): Observable<Metric[]> {
    return forkJoin(
      metricName.map((m) =>
        this.apiService.getDeploymentReplicaMetrics(deploymentId, replicaId, m)
      )
    ).pipe(
      map((list) => list.reduce((pre, cur) => [...pre, ...cur], [])),
      map((list) =>
        list
          .map((i) => {
            return {
              ...i,
              metric: {
                ...i.metric,
                name: this.metricServiceUtil.getMetricSeriesName(i.metric.name),
              },
            };
          })
          .sort((a, b) => {
            return (a.metric.handler || a.metric.name).localeCompare(
              b.metric.handler || b.metric.name
            );
          })
      )
    );
  }

  id(id: string): Observable<Deployment | undefined> {
    return this.list().pipe(map((list) => list.find((item) => item.id === id)));
  }

  refresh() {
    return this.apiService.listDeployments().pipe(
      map((item) => item.sort((a, b) => b.created_at - a.created_at)),
      tap((l) => this.list$.next(l))
    );
  }

  create(deployment: Partial<Deployment>): Observable<void> {
    return this.apiService.createDeployment(deployment);
  }

  delete(id: string): Observable<void> {
    return this.apiService.deleteDeployment(id);
  }
  update(id: string, deployment: Subset<Deployment>): Observable<void> {
    return this.apiService.updateDeployment(id, deployment);
  }

  request(name: string, request: OpenAPIRequest): Observable<unknown> {
    return this.apiService.requestDeployment(name, request);
  }

  getMetrics(deploymentId: string, metricName: string[]): Observable<Metric[]> {
    return forkJoin(
      metricName.map((m) =>
        this.apiService.getDeploymentMetrics(deploymentId, m)
      )
    ).pipe(
      map((list) => list.reduce((pre, cur) => [...pre, ...cur], [])),
      map((list) =>
        list.sort((a, b) => {
          return (a.metric.handler || a.metric.name).localeCompare(
            b.metric.handler || b.metric.name
          );
        })
      )
    );
  }
  constructor(
    private apiService: ApiService,
    private metricServiceUtil: MetricUtilService,
    private profileService: ProfileService
  ) {}
}
