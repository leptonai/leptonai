import { Injectable } from "injection-js";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { Observable, of } from "rxjs";
import { AuthorizedCluster } from "@lepton-dashboard/interfaces/cluster";
import { User } from "@lepton-dashboard/interfaces/user";
import { Session } from "@supabase/supabase-js";

@Injectable()
export class AuthNoopService implements AuthService {
  readonly client = null;

  getUserProfile(): Observable<User | null> {
    return of({ id: "test", email: "test@lepton.test", enable: true });
  }

  getSessionProfile(): Observable<Session["user"] | null> {
    return of({
      id: "",
      app_metadata: {},
      user_metadata: {},
      aud: "",
      created_at: "",
    });
  }

  listAuthorizedClusters(): Observable<AuthorizedCluster[]> {
    const host = import.meta.env.VITE_CLUSTER_URL || window.location.origin;
    return of([{ url: host, token: "" }]);
  }

  logout(): Promise<void> {
    return Promise.resolve(undefined);
  }
}
