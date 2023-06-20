import { Injectable } from "injection-js";
import { Observable } from "rxjs";
import { Photon } from "@lepton-dashboard/interfaces/photon";
import {
  Deployment,
  DeploymentEvent,
  Instance,
  Metric,
} from "@lepton-dashboard/interfaces/deployment";
import { ApiService } from "@lepton-dashboard/routers/workspace/services/api.service";
import { HttpClientService } from "@lepton-dashboard/services/http-client.service";
import { Subset } from "@lepton-dashboard/interfaces/subset";
import { OpenAPIRequest } from "@lepton-libs/open-api-tool";
import { WorkspaceTrackerService } from "./workspace-tracker.service";

@Injectable()
export class ApiServerService implements ApiService {
  private apiVersionPrefix = `/api/v1`;

  get host() {
    return this.workspaceTrackerService.cluster?.auth.url;
  }

  get prefix() {
    return `${this.host}${this.apiVersionPrefix}`;
  }

  listPhotons(): Observable<Photon[]> {
    return this.httpClientService.get(`${this.prefix}/photons`);
  }

  deletePhoton(id: string): Observable<void> {
    return this.httpClientService.delete(`${this.prefix}/photons/${id}`);
  }

  createPhoton(body: FormData): Observable<void> {
    return this.httpClientService.post(`${this.prefix}/photons`, body);
  }

  getPhotonDownloadUrl(id: string): string {
    return `${this.prefix}/photons/${id}?content=true`;
  }

  listDeployments(): Observable<Deployment[]> {
    return this.httpClientService.get(`${this.prefix}/deployments`);
  }

  createDeployment(deployment: Partial<Deployment>): Observable<void> {
    return this.httpClientService.post(`${this.prefix}/deployments`, {
      name: deployment.name,
      photon_id: deployment.photon_id,
      resource_requirement: deployment.resource_requirement,
      envs: deployment.envs || [],
    });
  }

  deleteDeployment(id: string): Observable<void> {
    return this.httpClientService.delete(`${this.prefix}/deployments/${id}`);
  }

  updateDeployment(
    id: string,
    deployment: Subset<Deployment>
  ): Observable<void> {
    return this.httpClientService.patch(
      `${this.prefix}/deployments/${id}`,
      deployment
    );
  }

  requestDeployment<T = unknown>(
    name: string,
    request: OpenAPIRequest
  ): Observable<T> {
    const url = new URL(request.url);
    // remove the host from the url
    const path = `${url.pathname}${url.search}${url.hash}`;
    const headers = {
      ...request.headers,
      deployment: name,
    };
    const data = request.body;
    return this.httpClientService.request({
      url: `${this.host}${path}`,
      method: request.method,
      headers,
      data,
    });
  }

  getDeploymentMetrics(
    deploymentId: string,
    metricName: string
  ): Observable<Metric[]> {
    return this.httpClientService.get(
      `${this.prefix}/deployments/${deploymentId}/monitoring/${metricName}`
    );
  }

  listDeploymentInstances(deploymentId: string): Observable<Instance[]> {
    return this.httpClientService.get(
      `${this.prefix}/deployments/${deploymentId}/instances`
    );
  }

  listDeploymentEvents(deploymentId: string): Observable<DeploymentEvent[]> {
    return this.httpClientService.get(
      `${this.prefix}/deployments/${deploymentId}/events`
    );
  }

  getDeploymentInstanceLogs(
    deploymentId: string,
    instanceId: string
  ): Observable<string> {
    return new Observable((subscriber) => {
      const abortController = new AbortController();
      let reader: ReadableStreamDefaultReader<string>;
      let record = "";
      const readInfinity = (response: Response) => {
        reader = response
          .body!.pipeThrough(new TextDecoderStream())
          .getReader();
        const pushToReader: (
          value: ReadableStreamReadResult<string>
        ) => string | PromiseLike<string> = ({ value, done }) => {
          if (done) {
            subscriber.complete();
            return record;
          }
          record += value;
          subscriber.next(record);
          return reader.read().then(pushToReader);
        };
        return reader.read().then(pushToReader);
      };
      fetch(
        `${this.prefix}/deployments/${deploymentId}/instances/${instanceId}/log`,
        {
          signal: abortController.signal,
        }
      ).then(readInfinity);
      return function unsubscribe() {
        abortController.abort();
      };
    });
  }

  getDeploymentInstanceSocketUrl(
    host: string,
    deploymentId: string,
    instanceId: string
  ): string {
    const hostname = new URL(host).hostname;
    return `wss://${hostname}/api/v1/deployments/${deploymentId}/instances/${instanceId}/shell`;
  }

  getDeploymentInstanceMetrics(
    deploymentId: string,
    instanceId: string,
    metricName: string
  ): Observable<Metric[]> {
    return this.httpClientService.get(
      `${this.prefix}/deployments/${deploymentId}/instances/${instanceId}/monitoring/${metricName}`
    );
  }

  constructor(
    private httpClientService: HttpClientService,
    private workspaceTrackerService: WorkspaceTrackerService
  ) {}
}
