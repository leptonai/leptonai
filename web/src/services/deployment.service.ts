import { Injectable } from "injection-js";
import { Observable, of } from "rxjs";
import { Deployment } from "@lepton-dashboard/interfaces/deployment.ts";

@Injectable()
export class DeploymentService {
  list(): Observable<Deployment[]> {
    return of([
      {
        id: "deployment-1",
        name: "dolly-v1.2",
        photon_id: "photon-1",
        status: {
          state: "terminated",
          endpoint: {
            internal_endpoint: "http://10.0.0.1:8000",
            external_endpoint: "https://example.com/dolly-v1.2",
          },
        },
        resource_requirement: {
          cpu: 4,
          memory: 4,
          min_replica: 1,
        },
      },
      {
        id: "deployment-2",
        name: "dolly-v1.3",
        photon_id: "photon-2",
        status: {
          state: "running",
          endpoint: {
            internal_endpoint: "http://10.0.0.2:8080",
            external_endpoint: "https://example.com/dolly-v1.3",
          },
        },
        resource_requirement: {
          cpu: 2,
          memory: 8,
          accelerator_type: "Nvidia V100",
          accelerator_num: 2,
          min_replica: 2,
        },
      },
      {
        id: "deployment-3",
        name: "dolly-v1.4",
        photon_id: "photon-3",
        status: {
          state: "running",
          endpoint: {
            internal_endpoint: "http://10.0.0.3:5000",
            external_endpoint: "https://example.com/dolly-v1.4",
          },
        },
        resource_requirement: {
          cpu: 8,
          memory: 16,
          accelerator_type: "Nvidia A100",
          accelerator_num: 4,
          min_replica: 3,
        },
      },
    ]);
  }
}
