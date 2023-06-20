import { Injectable } from "injection-js";
import { Observable } from "rxjs";
import { Photon } from "@lepton-dashboard/interfaces/photon";
import {
  Deployment,
  DeploymentEvent,
  Instance,
  Metric,
} from "@lepton-dashboard/interfaces/deployment";
import { Subset } from "@lepton-dashboard/interfaces/subset";
import { OpenAPIRequest } from "@lepton-libs/open-api-tool";

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

  abstract listDeploymentEvents(
    deploymentId: string
  ): Observable<DeploymentEvent[]>;

  abstract getDeploymentMetrics(
    deploymentId: string,
    metricName: string
  ): Observable<Metric[]>;
  abstract getDeploymentInstanceLogs(
    deploymentId: string,
    instanceId: string
  ): Observable<string>;
  abstract getDeploymentInstanceSocketUrl(
    host: string,
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
  abstract updateDeployment(
    id: string,
    deployment: Subset<Deployment>
  ): Observable<void>;
  abstract requestDeployment(
    name: string,
    request: OpenAPIRequest
  ): Observable<unknown>;
}
