import { Injectable } from "injection-js";
import { Session, SupabaseClient } from "@supabase/supabase-js";
import { Observable } from "rxjs";
import { AuthorizedCluster } from "@lepton-dashboard/interfaces/cluster";
import { User } from "@lepton-dashboard/interfaces/user";

@Injectable()
export abstract class AuthService {
  public readonly client: SupabaseClient | null = null;
  abstract getUserProfile(): Observable<User | null>;
  abstract getSessionProfile(): Observable<Session["user"] | null>;
  abstract listAuthorizedClusters(): Observable<AuthorizedCluster[]>;
  abstract logout(): Promise<void>;
}
