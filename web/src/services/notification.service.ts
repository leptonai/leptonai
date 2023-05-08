import { Injectable } from "injection-js";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { PhotonService } from "@lepton-dashboard/services/photon.service.ts";
import { map, mergeMap, take, tap } from "rxjs";
import { RefreshService } from "@lepton-dashboard/services/refresh.service.ts";

const DEPLOYMENT_TIME_KEY = "lepton-deployment-latest-date";
const PHOTON_TIME_KEY = "lepton-photon-latest-date";

@Injectable()
export class NotificationService {
  deploymentNotify$ = this.refreshService.refresh$.pipe(
    mergeMap(() => this.deploymentService.list()),
    map(([latest]) => {
      const cache = localStorage.getItem(DEPLOYMENT_TIME_KEY);
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
      const cache = localStorage.getItem(PHOTON_TIME_KEY);
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
          localStorage.setItem(DEPLOYMENT_TIME_KEY, `${latest.created_at}`);
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
          localStorage.setItem(PHOTON_TIME_KEY, `${latest.created_at}`);
        })
      )
      .subscribe();
  }

  constructor(
    private deploymentService: DeploymentService,
    private photonService: PhotonService,
    private refreshService: RefreshService
  ) {}
}
