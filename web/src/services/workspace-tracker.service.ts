import { Workspace } from "@lepton-dashboard/interfaces/workspace";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { Injectable } from "injection-js";

@Injectable()
export class WorkspaceTrackerService {
  id: string | null = null;

  workspace: Workspace | null = null;

  trackWorkspace(id: string) {
    this.id = id;
    this.workspace =
      this.profileService.profile?.authorized_workspaces?.find(
        (c) => c.auth.id === id
      ) || null;
  }

  constructor(private profileService: ProfileService) {}
}
