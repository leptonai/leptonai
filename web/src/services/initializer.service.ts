import { Injectable } from "injection-js";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service";
import { PhotonService } from "@lepton-dashboard/services/photon.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
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
            this.photonService.refresh(),
          ]);
        }),
        tap(() => this.initialized$.next(true))
      )
      .subscribe();
  }

  constructor(
    private deploymentService: DeploymentService,
    private photonService: PhotonService,
    private refreshService: RefreshService
  ) {}
}
