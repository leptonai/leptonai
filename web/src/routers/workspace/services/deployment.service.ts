import { MetricUtilService } from "@lepton-dashboard/routers/workspace/services/metric-util.service";
import { Injectable } from "injection-js";
import {
  BehaviorSubject,
  forkJoin,
  map,
  merge,
  Observable,
  of,
  tap,
} from "rxjs";
import {
  Deployment,
  Replica,
  DeploymentEvent,
  Metric,
  DeploymentReadiness,
  DeploymentTerminations,
} from "@lepton-dashboard/interfaces/deployment";
import { ApiService } from "@lepton-dashboard/routers/workspace/services/api.service";
import { Subset } from "@lepton-dashboard/interfaces/subset";
import { OpenAPIRequest } from "@lepton-libs/open-api-tool";
import { retryBackoff } from "@lepton-libs/rxjs/retry-backoff";

@Injectable()
export class DeploymentService {
  private endpointsConnectionsCache: Record<string, boolean> = {};
  private list$ = new BehaviorSubject<Deployment[]>([]);

  list(): Observable<Deployment[]> {
    return this.list$;
  }

  listReplicas(deploymentName: string): Observable<Replica[]> {
    return this.apiService.listDeploymentReplicas(deploymentName);
  }

  listEvents(deploymentName: string): Observable<DeploymentEvent[]> {
    return this.apiService.listDeploymentEvents(deploymentName);
  }

  getReadiness(deploymentName: string): Observable<DeploymentReadiness> {
    return this.apiService.getDeploymentReadiness(deploymentName);
  }

  getTerminations(deploymentName: string): Observable<DeploymentTerminations> {
    return this.apiService.getDeploymentTermination(deploymentName);
  }

  getReplicaLog(deploymentName: string, replicaId: string): Observable<string> {
    return this.apiService.getDeploymentReplicaLogs(deploymentName, replicaId);
  }

  getReplicaSocketUrl(deploymentName: string, replicaId: string): string {
    return this.apiService.getDeploymentReplicaSocketUrl(
      deploymentName,
      replicaId
    );
  }

  getReplicaMetrics(
    deploymentName: string,
    replicaId: string,
    metricName: string[]
  ): Observable<Metric[]> {
    return forkJoin(
      metricName.map((m) =>
        this.apiService.getDeploymentReplicaMetrics(
          deploymentName,
          replicaId,
          m
        )
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

  name(name: string): Observable<Deployment | undefined> {
    return this.list().pipe(
      map((list) => list.find((item) => item.name === name))
    );
  }

  refresh() {
    return this.apiService.listDeployments().pipe(
      retryBackoff({
        count: 5,
        delay: 1000,
      }),
      map((item) => item.sort((a, b) => b.created_at - a.created_at)),
      tap((l) => {
        this.list$.next(l);
        this.updateConnectionCacheKeys(
          l.map((i) => i.status.endpoint.external_endpoint)
        );
      })
    );
  }

  create(deployment: Partial<Deployment>): Observable<Deployment> {
    return this.apiService.createDeployment(deployment);
  }

  delete(name: string): Observable<void> {
    return this.apiService.deleteDeployment(name);
  }
  update(name: string, deployment: Subset<Deployment>): Observable<void> {
    return this.apiService.updateDeployment(name, deployment);
  }

  request(name: string, request: OpenAPIRequest): Observable<Response> {
    return this.apiService.requestDeployment(name, request);
  }

  getMetrics(
    deploymentName: string,
    metricName: string[]
  ): Observable<Metric[]> {
    return forkJoin(
      metricName.map((m) =>
        this.apiService.getDeploymentMetrics(deploymentName, m)
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

  endpointConnection(endpoint: string): Observable<boolean> {
    return merge(
      of(Boolean(this.endpointsConnectionsCache[endpoint])),
      this.refreshEndpointConnection(endpoint)
    );
  }

  private refreshEndpointConnection(endpoint: string): Observable<boolean> {
    return this.apiService.getEndpointConnection(endpoint).pipe(
      tap((health) => {
        if (Object.hasOwn(this.endpointsConnectionsCache, endpoint)) {
          this.endpointsConnectionsCache[endpoint] = health;
        }
      })
    );
  }

  private updateConnectionCacheKeys(keys: string[]) {
    this.endpointsConnectionsCache = keys.reduce((pre, cur) => {
      return {
        ...pre,
        [cur]: this.endpointsConnectionsCache[cur] || false,
      };
    }, {});
  }

  constructor(
    private apiService: ApiService,
    private metricServiceUtil: MetricUtilService
  ) {}
}
