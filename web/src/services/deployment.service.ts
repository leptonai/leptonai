import { Injectable } from "injection-js";
import { BehaviorSubject, map, Observable, tap } from "rxjs";
import {
  Deployment,
  Instance,
} from "@lepton-dashboard/interfaces/deployment.ts";
import { ApiService } from "@lepton-dashboard/services/api.service.ts";

@Injectable()
export class DeploymentService {
  private list$ = new BehaviorSubject<Deployment[]>([]);
  list(): Observable<Deployment[]> {
    return this.list$;
  }

  listInstances(deploymentId: string): Observable<Instance[]> {
    return this.apiService.listDeploymentInstances(deploymentId);
  }

  getInstanceLog(deploymentId: string, instanceId: string): Observable<string> {
    return this.apiService.getDeploymentInstanceLogs(deploymentId, instanceId);
  }

  getInstanceSocketUrl(deploymentId: string, instanceId: string): string {
    return this.apiService.getDeploymentInstanceSocketUrl(
      deploymentId,
      instanceId
    );
  }

  id(id: string): Observable<Deployment | undefined> {
    return this.list().pipe(map((list) => list.find((item) => item.id === id)));
  }

  refresh() {
    return this.apiService.listDeployments().pipe(
      map((item) => item.sort((a, b) => b.created_at - a.created_at)),
      tap((l) => this.list$.next(l))
    );
  }

  create(deployment: Partial<Deployment>): Observable<void> {
    return this.apiService.createDeployment(deployment);
  }

  delete(id: string): Observable<void> {
    return this.apiService.deleteDeployment(id);
  }
  update(id: string, miniReplicas: number): Observable<void> {
    return this.apiService.updateDeployment(id, miniReplicas);
  }

  request(name: string, value: string, path: string): Observable<unknown> {
    return this.apiService.requestDeployment(name, value, path);
  }
  constructor(private apiService: ApiService) {}
}
