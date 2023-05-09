import { Injectable } from "injection-js";
import { Observable } from "rxjs";
import { Photon } from "@lepton-dashboard/interfaces/photon.ts";
import { Deployment } from "@lepton-dashboard/interfaces/deployment.ts";

@Injectable()
export abstract class ApiService {
  abstract listPhotons(): Observable<Photon[]>;
  abstract deletePhoton(id: string): Observable<void>;
  abstract createPhoton(body: FormData): Observable<void>;

  abstract listDeployments(): Observable<Deployment[]>;
  abstract createDeployment(deployment: Partial<Deployment>): Observable<void>;
  abstract deleteDeployment(id: string): Observable<void>;
  abstract updateDeployment(id: string, miniReplicas: number): Observable<void>;
  abstract requestDeployment(url: string, value: string): Observable<unknown>;
}
