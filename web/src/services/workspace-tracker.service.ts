import { Workspace } from "@lepton-dashboard/interfaces/workspace";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { Injectable } from "injection-js";
import { TrackerService } from "@lepton-dashboard/services/tracker.service";
import { BehaviorSubject, Observable } from "rxjs";

@Injectable()
export class WorkspaceTrackerService {
  private workspace$ = new BehaviorSubject<Workspace | null>(null);

  id: string | null = null;

  workspace: Workspace | null = null;

  trackWorkspace(id: string) {
    this.id = id;
    this.workspace =
      this.profileService.profile?.authorized_workspaces?.find(
        (c) => c.auth.id === id
      ) || null;
    if (this.workspace && this.profileService.profile?.identification) {
      this.trackerService.identify(this.workspace.auth.id, {
        email: this.profileService.profile.identification.email,
        userId: this.profileService.profile.identification.id,
        workspaceId: this.workspace.auth.id,
      });
    }
    this.workspace$.next(this.workspace);
  }

  workspaceChanged(): Observable<Workspace | null> {
    return this.workspace$.asObservable();
  }

  constructor(
    private profileService: ProfileService,
    private trackerService: TrackerService
  ) {}
}
