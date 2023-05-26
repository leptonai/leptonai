import { Injectable } from "injection-js";
import { Observable } from "rxjs";
import { Photon } from "@lepton-dashboard/interfaces/photon";
import {
  Deployment,
  Instance,
  Metric,
} from "@lepton-dashboard/interfaces/deployment";

@Injectable()
export abstract class ApiService {
  abstract listPhotons(): Observable<Photon[]>;
  abstract deletePhoton(id: string): Observable<void>;
  abstract createPhoton(body: FormData): Observable<void>;
  abstract getPhotonDownloadUrl(id: string): string;

  abstract listDeployments(): Observable<Deployment[]>;
  abstract listDeploymentInstances(
    deploymentId: string
  ): Observable<Instance[]>;

  abstract getDeploymentInstanceLogs(
    deploymentId: string,
    instanceId: string
  ): Observable<string>;
  abstract getDeploymentInstanceSocketUrl(
    deploymentId: string,
    instanceId: string
  ): string;
  abstract getDeploymentInstanceMetrics(
    deploymentId: string,
    instanceId: string,
    metricName: string
  ): Observable<Metric[]>;
  abstract createDeployment(deployment: Partial<Deployment>): Observable<void>;
  abstract deleteDeployment(id: string): Observable<void>;
  abstract updateDeployment(id: string, miniReplicas: number): Observable<void>;
  abstract requestDeployment(
    url: string,
    value: string,
    path: string
  ): Observable<unknown>;
}
