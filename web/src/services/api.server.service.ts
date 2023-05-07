import { Injectable } from "injection-js";
import { Observable } from "rxjs";
import { Model } from "@lepton-dashboard/interfaces/model.ts";
import { Deployment } from "@lepton-dashboard/interfaces/deployment.ts";
import { ApiService } from "@lepton-dashboard/services/api.service.ts";
import { HttpClientService } from "@lepton-dashboard/services/http-client.service.ts";

@Injectable()
export class ApiServerService implements ApiService {
  private host =
    "https://vercel-proxy-one-murex.vercel.app/httpproxy/k8s-default-leptonse-42c1558c73-1362585501.us-east-1.elb.amazonaws.com";
  listModels(): Observable<Model[]> {
    return this.httpClientService.get(`${this.host}/photons`);
  }

  deleteModel(id: string): Observable<void> {
    return this.httpClientService.delete(`${this.host}/photons/${id}`);
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

  constructor(private httpClientService: HttpClientService) {}
}
