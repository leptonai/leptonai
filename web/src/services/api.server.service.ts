import { Injectable } from "injection-js";
import { Observable } from "rxjs";
import { Photon } from "@lepton-dashboard/interfaces/photon.ts";
import {
  Deployment,
  Instance,
} from "@lepton-dashboard/interfaces/deployment.ts";
import { ApiService } from "@lepton-dashboard/services/api.service.ts";
import { HttpClientService } from "@lepton-dashboard/services/http-client.service.ts";

@Injectable()
export class ApiServerService implements ApiService {
  private proxy = __PROXY_URL__;
  private cluster = __CLUSTER_URL__;
  private host = `${this.proxy}${this.cluster}/api/v1`;
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
    });
  }

  deleteDeployment(id: string): Observable<void> {
    return this.httpClientService.delete(`${this.host}/deployments/${id}`);
  }

  updateDeployment(id: string, miniReplicas: number): Observable<void> {
    return this.httpClientService.patch(`${this.host}/deployments/${id}`, {
      resource_requirement: {
        min_replicas: miniReplicas,
      },
    });
  }

  requestDeployment(
    name: string,
    value: string,
    path: string
  ): Observable<unknown> {
    return this.httpClientService.post(
      `${this.proxy}${this.cluster}${path}`,
      value,
      {
        headers: {
          deployment: name,
          "Content-Type": "application/json",
        },
      }
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
    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
    const host = window.location.host;
    return `${wsProtocol}://${host}/api/v1/deployments/${deploymentId}/instances/${instanceId}/shell`;
  }

  constructor(private httpClientService: HttpClientService) {}
}
