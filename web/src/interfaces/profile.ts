import { Session } from "@supabase/supabase-js";
import { Cluster } from "@lepton-dashboard/interfaces/cluster";
import { User } from "@lepton-dashboard/interfaces/user";

export interface Profile {
  identification: User | null;
  authorized_clusters: Cluster[];
  oauth: Session["user"] | null;
}
