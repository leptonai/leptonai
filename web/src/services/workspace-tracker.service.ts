import { Workspace } from "@lepton-dashboard/interfaces/workspace";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { Injectable } from "injection-js";

@Injectable()
export class WorkspaceTrackerService {
  name: string | null = null;

  workspace: Workspace | null = null;

  trackWorkspace(name: string) {
    this.name = name;
    this.workspace =
      this.profileService.profile?.authorized_workspaces?.find(
        (c) => c.data.workspace_name === name
      ) || null;
  }

  constructor(private profileService: ProfileService) {}
}
