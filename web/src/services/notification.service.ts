import { Injectable } from "injection-js";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { PhotonService } from "@lepton-dashboard/services/photon.service.ts";
import { map, mergeMap, take, tap } from "rxjs";
import { RefreshService } from "@lepton-dashboard/services/refresh.service.ts";
import { StorageService } from "@lepton-dashboard/services/storage.service.ts";

@Injectable()
export class NotificationService {
  deploymentNotify$ = this.refreshService.refresh$.pipe(
    mergeMap(() => this.deploymentService.list()),
    map(([latest]) => {
      const cache = this.storageService.get("DEPLOYMENT_TIME");
      if (!cache) {
        return true;
      } else {
        return latest && latest.created_at !== +cache;
      }
    })
  );

  photonNotify$ = this.refreshService.refresh$.pipe(
    mergeMap(() => this.photonService.list()),
    map(([latest]) => {
      const cache = this.storageService.get("PHOTON_TIME");
      if (!cache) {
        return true;
      } else {
        return latest && latest.created_at !== +cache;
      }
    })
  );

  updateDeploymentNotify() {
    this.deploymentService
      .list()
      .pipe(
        take(1),
        tap(([latest]) => {
          this.storageService.set("DEPLOYMENT_TIME", `${latest.created_at}`);
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
          this.storageService.set("PHOTON_TIME", `${latest.created_at}`);
        })
      )
      .subscribe();
  }

  constructor(
    private deploymentService: DeploymentService,
    private photonService: PhotonService,
    private refreshService: RefreshService,
    private storageService: StorageService
  ) {}
}
