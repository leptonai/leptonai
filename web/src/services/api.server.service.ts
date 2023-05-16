import { Injectable } from "injection-js";
import { Observable } from "rxjs";
import { Photon } from "@lepton-dashboard/interfaces/photon.ts";
import { Deployment } from "@lepton-dashboard/interfaces/deployment.ts";
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

  requestDeployment(url: string, value: string): Observable<unknown> {
    return this.httpClientService.post(`${this.proxy}${url}/run`, value, {
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  constructor(private httpClientService: HttpClientService) {}
}
