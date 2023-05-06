import { Injectable } from "injection-js";
import { map, Observable, of } from "rxjs";
import { Deployment } from "@lepton-dashboard/interfaces/deployment.ts";

@Injectable()
export class DeploymentService {
  list(): Observable<Deployment[]> {
    return of([
      {
        id: "8d14bcd1282bf94a52cf3b04fa46bcae",
        created_at: 1683229033569,
        name: "my-lepton-deployment",
        photon_id: "d9114fdefb8444c4c07804df1738b98e",
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
        photon_id: "d9114fdefb8444c4c07804df1738b98e",
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
    ]);
  }
  getById(id: string): Observable<Deployment | undefined> {
    return this.list().pipe(map((list) => list.find((item) => item.id === id)));
  }
}
