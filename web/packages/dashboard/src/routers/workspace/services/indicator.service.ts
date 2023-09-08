import { Injectable } from "injection-js";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { catchError, map, mergeMap, of, take, tap } from "rxjs";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { StorageService } from "@lepton-dashboard/services/storage.service";
import { WorkspaceTrackerService } from "../../../services/workspace-tracker.service";

@Injectable()
export class IndicatorService {
  deploymentNotify$ = this.refreshService.refresh$.pipe(
    mergeMap(() => this.deploymentService.list()),
    map(([latest]) => {
      const cache = this.storageService.get(
        this.workspaceTrackerService.id!,
        "DEPLOYMENT_TIME"
      );
      if (!cache) {
        return true;
      } else {
        return latest && latest.created_at !== +cache;
      }
    }),
    catchError(() => of(false))
  );

  photonNotify$ = this.refreshService.refresh$.pipe(
    mergeMap(() => this.photonService.list()),
    map(([latest]) => {
      const cache = this.storageService.get(
        this.workspaceTrackerService.id!,
        "PHOTON_TIME"
      );
      if (!cache) {
        return true;
      } else {
        return latest && latest.created_at !== +cache;
      }
    }),
    catchError(() => of(false))
  );

  updateDeploymentNotify() {
    this.deploymentService
      .list()
      .pipe(
        take(1),
        tap(([latest]) => {
          this.storageService.set(
            this.workspaceTrackerService.id!,
            "DEPLOYMENT_TIME",
            `${latest?.created_at}`
          );
        })
      )
      .subscribe();
  }

  updatePhotonNotify() {
    this.photonService
      .list()
      .pipe(
        take(1),
        tap(([latest]) => {
          this.storageService.set(
            this.workspaceTrackerService.id!,
            "PHOTON_TIME",
            `${latest?.created_at}`
          );
        })
      )
      .subscribe();
  }

  constructor(
    private deploymentService: DeploymentService,
    private photonService: PhotonService,
    private refreshService: RefreshService,
    private workspaceTrackerService: WorkspaceTrackerService,
    private storageService: StorageService
  ) {}
}
