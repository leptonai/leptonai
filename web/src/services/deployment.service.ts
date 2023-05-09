import { Injectable } from "injection-js";
import { BehaviorSubject, map, Observable, tap } from "rxjs";
import { Deployment } from "@lepton-dashboard/interfaces/deployment.ts";
import { ApiService } from "@lepton-dashboard/services/api.service.ts";

@Injectable()
export class DeploymentService {
  private list$ = new BehaviorSubject<Deployment[]>([]);
  list(): Observable<Deployment[]> {
    return this.list$;
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

  request(id: string, value: string): Observable<unknown> {
    return this.apiService.requestDeployment(id, value);
  }
  constructor(private apiService: ApiService) {}
}
