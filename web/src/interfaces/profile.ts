import { Workspace } from "@lepton-dashboard/interfaces/workspace";
import { User } from "@lepton-dashboard/interfaces/user";

export interface Profile {
  identification: User | null;
  authorized_workspaces: Workspace[];
}
