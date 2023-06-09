import { Cluster } from "@lepton-dashboard/interfaces/cluster";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { Injectable } from "injection-js";

@Injectable()
export class WorkspaceTrackerService {
  name: string | null = null;

  cluster: Cluster | null = null;

  trackWorkspace(name: string) {
    this.name = name;
    this.cluster =
      this.profileService.profile?.authorized_clusters?.find(
        (c) => c.data.cluster_name === name
      ) || null;
  }

  constructor(private profileService: ProfileService) {}
}
