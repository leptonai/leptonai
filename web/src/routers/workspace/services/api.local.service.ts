import { Secret } from "@lepton-dashboard/interfaces/secret";
import { Injectable } from "injection-js";
import { EMPTY, Observable, of } from "rxjs";
import { Photon } from "@lepton-dashboard/interfaces/photon";
import {
  Deployment,
  DeploymentEvent,
  Replica,
  Metric,
} from "@lepton-dashboard/interfaces/deployment";
import { ApiService } from "@lepton-dashboard/routers/workspace/services/api.service";
import { Subset } from "@lepton-dashboard/interfaces/subset";
import { OpenAPIRequest } from "@lepton-libs/open-api-tool";
import { FineTuneJob } from "@lepton-dashboard/interfaces/fine-tune";
const mockedPhotons = [
  {
    id: "dd3f54cb-56e4-494d-8e0b-b5a004f373f5",
    name: "example-photon-1",
    model: "hf:example/1.0.0",
    requirement_dependency: [
      "numpy==1.19.3",
      "torch==1.10.0",
      "transformers==4.15.0",
    ],
    image: "docker.io/library/python:3.9.6-slim-buster",
    entrypoint: "python main.py",
    exposed_ports: [8000],
    created_at: 1651497985000,
  },
  {
    id: "f166e6d5-7271-423f-a1a8-82f9aa4c04cf",
    name: "example-photon-2",
    model: "hf:example/1.1.0",
    image: "docker.io/library/python:3.9.6-slim-buster",
    entrypoint: "python main.py",
    exposed_ports: [8080],
    container_args: ["--shm-size=2g"],
    created_at: 1651608499000,
  },
  {
    id: "2db34eb3-b573-475c-800a-893def98ef72",
    name: "example-photon-3",
    model: "hf:example/2.0.0",
    requirement_dependency: ["tensorflow==2.6.0", "keras==2.6.0"],
    image: "docker.io/library/tensorflow:2.6.0",
    exposed_ports: [5000],
    container_args: ["--gpus=all", "--env", "CUDA_VISIBLE_DEVICES=0"],
    created_at: 1651862976000,
  },
  {
    id: "c57888fe-019c-49a0-a355-9adf2049e1af",
    name: "example-photon-3",
    model: "hf:example/2.1.0",
    requirement_dependency: ["tensorflow==2.7.0", "keras==2.7.0"],
    image: "docker.io/library/tensorflow:2.7.0",
    entrypoint: "python main.py",
    exposed_ports: [5000],
    container_args: ["--gpus=all", "--env", "CUDA_VISIBLE_DEVICES=0"],
    created_at: 1651926176000,
  },
];
const mockedDeployments = [
  {
    id: "8d14bcd1282bf94a52cf3b04fa46bcae",
    created_at: 1683229033569,
    name: "my-lepton-deployment",
    photon_id: "dd3f54cb-56e4-494d-8e0b-b5a004f373f5",
    status: {
      state: "running",
      endpoint: { internal_endpoint: "", external_endpoint: "" },
    },
    resource_requirement: {
      cpu: 1,
      memory: 8192,
      accelerator_type: "nvidia-tesla-p100",
      accelerator_num: 2,
      min_replicas: 1,
    },
  },
  {
    id: "97d2ca52c18149e2832b103b73551dae",
    created_at: 1683255310712,
    name: "my-lepton-deployment",
    photon_id: "dd3f54cb-56e4-494d-8e0b-b5a004f373f5",
    status: {
      state: "running",
      endpoint: { internal_endpoint: "", external_endpoint: "" },
    },
    resource_requirement: {
      cpu: 1,
      memory: 8192,
      accelerator_type: "nvidia-tesla-p100",
      accelerator_num: 2,
      min_replicas: 1,
    },
  },
];

@Injectable()
export class ApiLocalService implements ApiService {
  listPhotons(): Observable<Photon[]> {
    return of(mockedPhotons);
  }

  deletePhoton(id: string): Observable<void> {
    console.log(id);
    return EMPTY;
  }

  createPhoton(body: FormData): Observable<void> {
    console.log(body);
    return EMPTY;
  }

  getPhotonDownloadUrl(id: string): string {
    return id;
  }

  listDeployments(): Observable<Deployment[]> {
    return of(mockedDeployments);
  }

  createDeployment(deployment: Partial<Deployment>): Observable<void> {
    console.log(deployment);
    return EMPTY;
  }

  deleteDeployment(id: string): Observable<void> {
    console.log(id);
    return EMPTY;
  }

  listDeploymentReplicas(deploymentId: string): Observable<Replica[]> {
    console.log(deploymentId);
    return of([]);
  }

  listDeploymentEvents(deploymentId: string): Observable<DeploymentEvent[]> {
    console.log(deploymentId);
    return of([]);
  }

  updateDeployment(
    id: string,
    deployment: Subset<Deployment>
  ): Observable<void> {
    console.log(id, deployment);
    return EMPTY;
  }

  requestDeployment(url: string, request: OpenAPIRequest): Observable<void> {
    console.log(url, request);
    return EMPTY;
  }

  getDeploymentMetrics(
    deploymentId: string,
    metricName: string
  ): Observable<Metric[]> {
    console.log(deploymentId, metricName);
    return of([
      {
        metric: { name: "demo" },
        values: [],
      },
    ]);
  }

  getDeploymentReplicaLogs(
    deploymentId: string,
    replicaId: string
  ): Observable<string> {
    console.log(deploymentId, replicaId);
    return of("");
  }

  getDeploymentReplicaSocketUrl(
    host: string,
    deploymentId: string,
    replicaId: string
  ): string {
    console.log(host, deploymentId, replicaId);
    return "";
  }

  getDeploymentReplicaMetrics(
    deploymentId: string,
    replicaId: string,
    metricName: string
  ): Observable<Metric[]> {
    console.log(deploymentId, replicaId, metricName);
    return of([
      {
        metric: { name: "demo" },
        values: [],
      },
    ]);
  }

  createSecret(secret: Secret): Observable<void> {
    console.log(secret);
    return EMPTY;
  }
  listSecrets(): Observable<string[]> {
    return of([]);
  }
  deleteSecret(id: string): Observable<void> {
    console.log(id);
    return EMPTY;
  }

  cancelFineTuneJob(_id: number): Observable<void> {
    return EMPTY;
  }

  addFineTuneJob(_file: File): Observable<FineTuneJob> {
    return EMPTY;
  }

  getFineTuneJob(_id: number): Observable<FineTuneJob> {
    return EMPTY;
  }

  listFineTuneJobs(): Observable<FineTuneJob[]> {
    return EMPTY;
  }
}
