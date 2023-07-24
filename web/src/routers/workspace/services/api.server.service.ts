import { Secret } from "@lepton-dashboard/interfaces/secret";
import { Injectable } from "injection-js";
import { catchError, Observable, of } from "rxjs";
import { Photon } from "@lepton-dashboard/interfaces/photon";
import {
  Deployment,
  DeploymentEvent,
  DeploymentReadiness,
  DeploymentTerminations,
  Metric,
  Replica,
} from "@lepton-dashboard/interfaces/deployment";
import { ApiService } from "@lepton-dashboard/routers/workspace/services/api.service";
import {
  HttpClientService,
  HttpContext,
} from "@lepton-dashboard/services/http-client.service";
import { Subset } from "@lepton-dashboard/interfaces/subset";
import { OpenAPIRequest } from "@lepton-libs/open-api-tool";
import Stripe from "stripe";
import { WorkspaceTrackerService } from "../../../services/workspace-tracker.service";
import {
  FineTuneJob,
  FineTuneJobStatus,
} from "@lepton-dashboard/interfaces/fine-tune";
import { FileInfo } from "@lepton-dashboard/interfaces/storage";
import { INTERCEPTOR_CONTEXT } from "@lepton-dashboard/interceptors/app.interceptor.context";

@Injectable()
export class ApiServerService implements ApiService {
  private apiVersionPrefix = `/api/v1`;

  get host() {
    return this.workspaceTrackerService.workspace?.auth.url;
  }

  get token() {
    return this.workspaceTrackerService.workspace?.auth.token;
  }

  get prefix() {
    return this.host
      ? new URL(this.apiVersionPrefix, this.host).href
      : this.apiVersionPrefix;
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
      resource_requirement: {
        min_replicas: deployment.resource_requirement?.min_replicas,
        resource_shape: deployment.resource_requirement?.resource_shape,
      },
      api_tokens: deployment.api_tokens || [],
      envs: deployment.envs || [],
      mounts: deployment.mounts || [],
    });
  }

  deleteDeployment(name: string): Observable<void> {
    return this.httpClientService.delete(`${this.prefix}/deployments/${name}`);
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

  requestDeployment(
    name: string,
    request: OpenAPIRequest
  ): Observable<Response> {
    return new Observable<Response>((subscriber) => {
      const url = new URL(request.url);
      // remove the host from the url
      const path = `${url.pathname}${url.search}${url.hash}`;
      const data = request.body;
      const headers = new Headers();
      Object.entries(request.headers).forEach(([key, value]) => {
        headers.append(key, value);
      });
      headers.append("Authorization", `Bearer ${this.token}`);
      headers.append("X-Lepton-Deployment", name);

      const abortController = new AbortController();
      fetch(`${this.host}${path}`, {
        method: request.method,
        headers: headers,
        body: JSON.stringify(data),
        signal: abortController.signal,
      })
        .then((response) => {
          if (!response.ok) {
            subscriber.error(response);
          }
          subscriber.next(response);
          subscriber.complete();
        })
        .catch((err) => {
          subscriber.error(err);
        });
      return () => {
        if (subscriber.closed) {
          return;
        }
        abortController.abort();
      };
    });
  }

  getDeploymentMetrics(
    deploymentName: string,
    metricName: string
  ): Observable<Metric[]> {
    return this.httpClientService.get(
      `${this.prefix}/deployments/${deploymentName}/monitoring/${metricName}`,
      {
        context: new HttpContext().set(INTERCEPTOR_CONTEXT, {
          ignoreErrors: [500],
        }),
      }
    );
  }

  listDeploymentReplicas(deploymentName: string): Observable<Replica[]> {
    return this.httpClientService.get(
      `${this.prefix}/deployments/${deploymentName}/replicas`
    );
  }

  listDeploymentEvents(deploymentName: string): Observable<DeploymentEvent[]> {
    return this.httpClientService.get(
      `${this.prefix}/deployments/${deploymentName}/events`
    );
  }

  getDeploymentReadiness(
    deploymentName: string
  ): Observable<DeploymentReadiness> {
    return this.httpClientService
      .get<DeploymentReadiness>(
        `${this.prefix}/deployments/${deploymentName}/readiness`
      )
      .pipe(
        catchError((err) => {
          if (err?.response?.status === 404) {
            return of({});
          }
          throw err;
        })
      );
  }

  getDeploymentTermination(
    deploymentName: string
  ): Observable<DeploymentTerminations> {
    return this.httpClientService.get(
      `${this.prefix}/deployments/${deploymentName}/termination`
    );
  }

  getDeploymentReplicaLogs(
    deploymentName: string,
    replicaId: string
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
        `${this.prefix}/deployments/${deploymentName}/replicas/${replicaId}/log`,
        {
          headers: {
            Authorization: `Bearer ${this.token}`,
          },
          signal: abortController.signal,
        }
      ).then(readInfinity);
      return function unsubscribe() {
        abortController.abort();
      };
    });
  }

  getDeploymentReplicaSocketUrl(
    host: string,
    deploymentName: string,
    replicaId: string
  ): string {
    return `wss://${host}/api/v1/deployments/${deploymentName}/replicas/${replicaId}/shell`;
  }

  getDeploymentReplicaMetrics(
    deploymentName: string,
    replicaId: string,
    metricName: string
  ): Observable<Metric[]> {
    return this.httpClientService.get(
      `${this.prefix}/deployments/${deploymentName}/replicas/${replicaId}/monitoring/${metricName}`,
      {
        context: new HttpContext().set(INTERCEPTOR_CONTEXT, {
          ignoreErrors: [500],
        }),
      }
    );
  }

  createSecret(secret: Secret): Observable<void> {
    return this.httpClientService.post(
      `${this.prefix}/secrets`,
      JSON.stringify([secret])
    );
  }

  listSecrets(): Observable<string[]> {
    return this.httpClientService.get(`${this.prefix}/secrets`);
  }

  deleteSecret(id: string): Observable<void> {
    return this.httpClientService.delete(`${this.prefix}/secrets/${id}`);
  }

  listFineTuneJobs(status?: FineTuneJobStatus): Observable<FineTuneJob[]> {
    return this.httpClientService.get<FineTuneJob[]>(
      `${this.prefix}/tuna/job/list${status ? `/${status}` : ""}`
    );
  }

  addFineTuneJob(file: File): Observable<FineTuneJob> {
    const formData = new FormData();
    formData.append("data", file);
    return this.httpClientService.post<FineTuneJob>(
      `${this.prefix}/tuna/job/add`,
      formData,
      {
        params: {
          name: file.name,
        },
      }
    );
  }

  cancelFineTuneJob(id: number): Observable<void> {
    return this.httpClientService.get<void>(
      `${this.prefix}/tuna/job/cancel/${id}`
    );
  }

  getFineTuneJob(id: number): Observable<FineTuneJob> {
    return this.httpClientService.get<FineTuneJob>(
      `${this.prefix}/tuna/job/${id}`
    );
  }

  uploadStorageFile(path: string, file: File): Observable<void> {
    const formData = new FormData();
    formData.append("file", file);
    return this.httpClientService.post<void>(
      `${this.prefix}/storage/${path}`,
      formData
    );
  }

  removeStorageEntry(path: string): Observable<void> {
    return this.httpClientService.delete<void>(
      `${this.prefix}/storage/${path}`
    );
  }

  listStorageEntries(path: string): Observable<FileInfo[]> {
    return this.httpClientService.get<FileInfo[]>(
      `${this.prefix}/storage/${path}`
    );
  }

  makeStorageDirectory(path: string): Observable<void> {
    return this.httpClientService.put<void>(`${this.prefix}/storage/${path}`);
  }

  getPortal(): Observable<{ url: string }> {
    return this.httpClientService.post<{ url: string }>(
      `https://portal.lepton.ai/api/billing/portal`,
      {
        workspace_id: this.workspaceTrackerService.id,
      },
      {
        withCredentials: true,
      }
    );
  }

  getInvoice() {
    return this.httpClientService.post<{
      products: Stripe.Product[];
      upcoming?: Stripe.UpcomingInvoice;
      open?: Stripe.Invoice;
    }>(
      `https://portal.lepton.ai/api/billing/invoice`,
      {
        workspace_id: this.workspaceTrackerService.id,
      },
      {
        withCredentials: true,
      }
    );
  }

  constructor(
    private httpClientService: HttpClientService,
    private workspaceTrackerService: WorkspaceTrackerService
  ) {}
}
