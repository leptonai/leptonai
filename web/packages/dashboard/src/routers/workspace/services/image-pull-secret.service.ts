import { ApiService } from "@lepton-dashboard/routers/workspace/services/api.service";
import { Injectable } from "injection-js";
import { ImagePullSecret } from "@lepton-dashboard/interfaces/image-pull-secrets";
import { BehaviorSubject, catchError, switchMap, tap } from "rxjs";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";

@Injectable()
export class ImagePullSecretService {
  // FIXME: remove this when the backend is all ready
  available$ = new BehaviorSubject<boolean>(false);

  constructor(
    private apiService: ApiService,
    private workspaceTrackerService: WorkspaceTrackerService
  ) {
    // FIXME: remove this when the backend is all ready
    // self-check the availability of image pull secrets
    this.workspaceTrackerService
      .workspaceChanged()
      .pipe(switchMap(() => this.listImagePullSecrets()))
      .subscribe();
  }

  listImagePullSecrets() {
    return this.apiService.listImagePullSecrets().pipe(
      tap({
        next: () => this.available$.next(true),
        error: () => this.available$.next(false),
      }),
      catchError(() => {
        return [];
      })
    );
  }

  createImagePullSecret(secret: ImagePullSecret) {
    return this.apiService.createImagePullSecret(secret);
  }

  deleteImagePullSecret(name: string) {
    return this.apiService.deleteImagePullSecret(name);
  }
}
