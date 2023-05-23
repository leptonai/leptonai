import { Injectable } from "injection-js";
import { interval, Observable, startWith, Subject, takeUntil } from "rxjs";
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
        min_replica: miniReplicas,
      },
    });
  }

  requestDeployment(name: string, value: string): Observable<unknown> {
    return this.httpClientService.post(
      `${this.proxy}${this.cluster}/run`,
      value,
      {
        headers: {
          LeptonDeployment: name,
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
      const continuePolling$ = new Subject<void>();
      let reader: ReadableStreamDefaultReader<string>;
      let record = "";
      const interval$ = interval(50);
      fetch(
        `${this.host}/deployments/${deploymentId}/instances/${instanceId}/log`
      ).then((response) => {
        if (response.body) {
          reader = response.body
            .pipeThrough(new TextDecoderStream())
            .getReader();
          const callReader = () =>
            reader.read().then(({ done, value }) => {
              if (done) {
                subscriber.complete();
              } else {
                record = record + value;
                subscriber.next(record);
              }
            });
          interval$
            .pipe(takeUntil(continuePolling$), startWith(true))
            .subscribe(() => {
              void callReader();
            });
        }
      });
      return function unsubscribe() {
        continuePolling$.next();
        if (reader) {
          void reader.cancel();
        }
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
