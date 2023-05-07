import { Injectable } from "injection-js";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { ModelService } from "@lepton-dashboard/services/model.service.ts";
import { RefreshService } from "@lepton-dashboard/services/refresh.service.ts";
import { BehaviorSubject, forkJoin, switchMap, tap } from "rxjs";

@Injectable()
export class InitializerService {
  initialized$ = new BehaviorSubject(false);
  bootstrap() {
    this.refreshService.refresh$
      .pipe(
        switchMap(() => {
          return forkJoin([
            this.deploymentService.refresh(),
            this.modelService.refresh(),
          ]);
        }),
        tap(() => this.initialized$.next(true))
      )
      .subscribe();
  }

  constructor(
    private deploymentService: DeploymentService,
    private modelService: ModelService,
    private refreshService: RefreshService
  ) {}
}
