import { Injectable } from "injection-js";
import { Observable } from "rxjs";
import { Model } from "@lepton-dashboard/interfaces/model.ts";
import { Deployment } from "@lepton-dashboard/interfaces/deployment.ts";

@Injectable()
export abstract class ApiService {
  abstract listModels(): Observable<Model[]>;
  abstract deleteModel(id: string): Observable<void>;

  abstract listDeployments(): Observable<Deployment[]>;
  abstract createDeployment(deployment: Partial<Deployment>): Observable<void>;
  abstract deleteDeployment(id: string): Observable<void>;
  abstract updateDeployment(id: string, miniReplicas: number): Observable<void>;
}
