import { Injectable } from "injection-js";
import { Observable } from "rxjs";
import { Photon } from "@lepton-dashboard/interfaces/photon.ts";
import { Deployment } from "@lepton-dashboard/interfaces/deployment.ts";
import { ApiService } from "@lepton-dashboard/services/api.service.ts";
import { HttpClientService } from "@lepton-dashboard/services/http-client.service.ts";

@Injectable()
export class ApiServerService implements ApiService {
  private prefix = `https://rewrites-five.vercel.app/httpproxy/`;
  private cluster = `k8s-default-leptonse-42c1558c73-673051545.us-east-1.elb.amazonaws.com`;
  private host = `${this.prefix}${this.cluster}`;
  listPhotons(): Observable<Photon[]> {
    return this.httpClientService.get(`${this.host}/photons`);
  }

  deletePhoton(id: string): Observable<void> {
    return this.httpClientService.delete(`${this.host}/photons/${id}`);
  }

  createPhoton(body: FormData): Observable<void> {
    return this.httpClientService.post(`${this.host}/photons`, body);
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
    return this.httpClientService.post(`${this.prefix}${url}/run`, value, {
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  constructor(private httpClientService: HttpClientService) {}
}
