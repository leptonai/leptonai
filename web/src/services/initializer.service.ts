import { Injectable } from "injection-js";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service";
import { PhotonService } from "@lepton-dashboard/services/photon.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { BehaviorSubject, combineLatest, forkJoin, switchMap, tap } from "rxjs";
import { ClusterService } from "@lepton-dashboard/services/cluster.service";

@Injectable()
export class InitializerService {
  initialized$ = new BehaviorSubject(false);
  bootstrap() {
    combineLatest([
      this.clusterService.getCurrentClusterInfo(),
      this.refreshService.refresh$.pipe(
        switchMap(() => {
          return forkJoin([
            this.deploymentService.refresh(),
            this.photonService.refresh(),
          ]);
        })
      ),
    ])
      .pipe(tap(() => this.initialized$.next(true)))
      .subscribe();
  }

  constructor(
    private deploymentService: DeploymentService,
    private photonService: PhotonService,
    private clusterService: ClusterService,
    private refreshService: RefreshService
  ) {}
}
