import { Injectable } from "injection-js";
import { Observable } from "rxjs";
import { Photon } from "@lepton-dashboard/interfaces/photon";
import {
  Deployment,
  Instance,
  Metric,
} from "@lepton-dashboard/interfaces/deployment";
import { ApiService } from "@lepton-dashboard/services/api.service";
import { HttpClientService } from "@lepton-dashboard/services/http-client.service";
import { Subset } from "@lepton-dashboard/interfaces/subset";
import { Cluster } from "@lepton-dashboard/interfaces/cluster";

@Injectable()
export class ApiServerService implements ApiService {
  private host = import.meta.env.PROD
    ? `${import.meta.env.VITE_CLUSTER_URL}/api/v1`
    : "/api/v1";
  listPhotons(): Observable<Photon[]> {
    return this.httpClientService.get(`${this.host}/photons`);
  }

  deletePhoton(id: string): Observable<void> {
    return this.httpClientService.delete(`${this.host}/photons/${id}`);
  }

  createPhoton(body: FormData): Observable<void> {
    return this.httpClientService.post(`${this.host}/photons`, body);
  }

  getPhotonDownloadUrl(id: string): string {
    return `${this.host}/photons/${id}?content=true`;
  }

  listDeployments(): Observable<Deployment[]> {
    return this.httpClientService.get(`${this.host}/deployments`);
  }

  createDeployment(deployment: Partial<Deployment>): Observable<void> {
    return this.httpClientService.post(`${this.host}/deployments`, {
      name: deployment.name,
      photon_id: deployment.photon_id,
      resource_requirement: deployment.resource_requirement,
      envs: deployment.envs || [],
    });
  }

  deleteDeployment(id: string): Observable<void> {
    return this.httpClientService.delete(`${this.host}/deployments/${id}`);
  }

  updateDeployment(
    id: string,
    deployment: Subset<Deployment>
  ): Observable<void> {
    return this.httpClientService.patch(
      `${this.host}/deployments/${id}`,
      deployment
    );
  }

  requestDeployment(
    name: string,
    value: string,
    path: string
  ): Observable<unknown> {
    return this.httpClientService.post(
      `${import.meta.env.VITE_CLUSTER_URL}${path}`,
      value,
      {
        headers: {
          deployment: name,
          "Content-Type": "application/json",
        },
      }
    );
  }

  getDeploymentMetrics(
    deploymentId: string,
    metricName: string
  ): Observable<Metric[]> {
    return this.httpClientService.get(
      `${this.host}/deployments/${deploymentId}/monitoring/${metricName}`
    );
  }

  listDeploymentInstances(deploymentId: string): Observable<Instance[]> {
    return this.httpClientService.get(
      `${this.host}/deployments/${deploymentId}/instances`
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
        `${this.host}/deployments/${deploymentId}/instances/${instanceId}/log`,
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
    deploymentId: string,
    instanceId: string
  ): string {
    const host =
      new URL(import.meta.env.VITE_CLUSTER_URL).host || window.location.host;
    return `wss://${host}/api/v1/deployments/${deploymentId}/instances/${instanceId}/shell`;
  }

  getDeploymentInstanceMetrics(
    deploymentId: string,
    instanceId: string,
    metricName: string
  ): Observable<Metric[]> {
    return this.httpClientService.get(
      `${this.host}/deployments/${deploymentId}/instances/${instanceId}/monitoring/${metricName}`
    );
  }

  getClusterInfo(): Observable<Cluster> {
    return this.httpClientService.get(`${this.host}/cluster`);
  }

  constructor(private httpClientService: HttpClientService) {}
}
