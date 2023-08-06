import { Secret } from "@lepton-dashboard/interfaces/secret";
import { Injectable } from "injection-js";
import { Observable } from "rxjs";
import { Photon } from "@lepton-dashboard/interfaces/photon";
import {
  Deployment,
  DeploymentEvent,
  Replica,
  Metric,
  DeploymentReadiness,
  DeploymentTerminations,
} from "@lepton-dashboard/interfaces/deployment";
import { Subset } from "@lepton-dashboard/interfaces/subset";
import { OpenAPIRequest } from "@lepton-libs/open-api-tool";
import {
  FineTuneJob,
  FineTuneJobStatus,
  TunaInference,
} from "@lepton-dashboard/interfaces/fine-tune";
import { FileInfo } from "@lepton-dashboard/interfaces/storage";
import Stripe from "stripe";
@Injectable()
export abstract class ApiService {
  abstract listPhotons(): Observable<Photon[]>;
  abstract deletePhoton(id: string): Observable<void>;
  abstract createPhoton(body: FormData): Observable<void>;
  abstract getPhotonDownloadUrl(id: string): string;

  abstract listDeployments(): Observable<Deployment[]>;
  abstract listDeploymentReplicas(
    deploymentName: string
  ): Observable<Replica[]>;

  abstract listDeploymentEvents(
    deploymentName: string
  ): Observable<DeploymentEvent[]>;

  abstract getDeploymentReadiness(
    deploymentName: string
  ): Observable<DeploymentReadiness>;

  abstract getDeploymentTermination(
    deploymentName: string
  ): Observable<DeploymentTerminations>;

  abstract getDeploymentMetrics(
    deploymentName: string,
    metricName: string
  ): Observable<Metric[]>;
  abstract getDeploymentReplicaLogs(
    deploymentName: string,
    replicaId: string
  ): Observable<string>;
  abstract getDeploymentReplicaSocketUrl(
    deploymentName: string,
    replicaId: string
  ): string;
  abstract getDeploymentReplicaMetrics(
    deploymentName: string,
    replicaId: string,
    metricName: string
  ): Observable<Metric[]>;
  abstract createDeployment(deployment: Partial<Deployment>): Observable<void>;
  abstract deleteDeployment(name: string): Observable<void>;
  abstract updateDeployment(
    name: string,
    deployment: Subset<Deployment>
  ): Observable<void>;
  abstract requestDeployment(
    name: string,
    request: OpenAPIRequest
  ): Observable<Response>;

  abstract createSecret(secret: Secret): Observable<void>;
  abstract listSecrets(): Observable<string[]>;
  abstract deleteSecret(id: string): Observable<void>;

  abstract listFineTuneJobs(
    status?: FineTuneJobStatus
  ): Observable<FineTuneJob[]>;
  abstract addFineTuneJob(name: string, file: File): Observable<FineTuneJob>;
  abstract cancelFineTuneJob(id: number): Observable<void>;
  abstract getFineTuneJob(id: number): Observable<FineTuneJob>;

  abstract createInference(tunaInference: TunaInference): Observable<void>;
  abstract deleteInference(name: string): Observable<void>;
  abstract getInference(name: string): Observable<TunaInference | null>;

  abstract listStorageEntries(path: string): Observable<FileInfo[]>;
  abstract makeStorageDirectory(path: string): Observable<void>;
  abstract uploadStorageFile(path: string, file: File): Observable<void>;
  abstract removeStorageEntry(path: string): Observable<void>;

  abstract getPortal(): Observable<{ url: string }>;
  abstract getInvoice(): Observable<{
    upcoming?: Stripe.UpcomingInvoice;
    open?: Stripe.Invoice;
    products: Stripe.Product[];
    list: Stripe.Invoice[];
  }>;
}
