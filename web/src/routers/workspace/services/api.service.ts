import { Secret } from "@lepton-dashboard/interfaces/secret";
import { Injectable } from "injection-js";
import { Observable } from "rxjs";
import { Photon } from "@lepton-dashboard/interfaces/photon";
import {
  Deployment,
  DeploymentEvent,
  Replica,
  Metric,
} from "@lepton-dashboard/interfaces/deployment";
import { Subset } from "@lepton-dashboard/interfaces/subset";
import { OpenAPIRequest } from "@lepton-libs/open-api-tool";
import {
  FineTuneJob,
  FineTuneJobStatus,
} from "@lepton-dashboard/interfaces/fine-tune";
import { FileInfo } from "@lepton-dashboard/interfaces/storage";

@Injectable()
export abstract class ApiService {
  abstract listPhotons(): Observable<Photon[]>;
  abstract deletePhoton(id: string): Observable<void>;
  abstract createPhoton(body: FormData): Observable<void>;
  abstract getPhotonDownloadUrl(id: string): string;

  abstract listDeployments(): Observable<Deployment[]>;
  abstract listDeploymentReplicas(deploymentId: string): Observable<Replica[]>;

  abstract listDeploymentEvents(
    deploymentId: string
  ): Observable<DeploymentEvent[]>;

  abstract getDeploymentMetrics(
    deploymentId: string,
    metricName: string
  ): Observable<Metric[]>;
  abstract getDeploymentReplicaLogs(
    deploymentId: string,
    replicaId: string
  ): Observable<string>;
  abstract getDeploymentReplicaSocketUrl(
    host: string,
    deploymentId: string,
    replicaId: string
  ): string;
  abstract getDeploymentReplicaMetrics(
    deploymentId: string,
    replicaId: string,
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

  abstract createSecret(secret: Secret): Observable<void>;
  abstract listSecrets(): Observable<string[]>;
  abstract deleteSecret(id: string): Observable<void>;

  abstract listFineTuneJobs(
    status?: FineTuneJobStatus
  ): Observable<FineTuneJob[]>;
  abstract addFineTuneJob(file: File): Observable<FineTuneJob>;
  abstract cancelFineTuneJob(id: number): Observable<void>;
  abstract getFineTuneJob(id: number): Observable<FineTuneJob>;

  abstract listStorageEntries(path: string): Observable<FileInfo[]>;
  abstract makeStorageDirectory(path: string): Observable<void>;
  abstract uploadStorageFile(path: string, file: File): Observable<void>;
  abstract removeStorageEntry(path: string): Observable<void>;
}
