import { Injectable } from "injection-js";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { Observable, of } from "rxjs";
import { AuthorizedCluster } from "@lepton-dashboard/interfaces/cluster";
import { User } from "@lepton-dashboard/interfaces/user";
import { Session } from "@supabase/supabase-js";
import { StorageService } from "@lepton-dashboard/services/storage.service";

@Injectable()
export class AuthTokenService implements AuthService {
  readonly client = null;

  constructor(private storageService: StorageService) {}

  private getTokenMapFromStorage(): string {
    return (
      this.storageService.get(StorageService.GLOBAL_SCOPE, "CLUSTER_TOKEN") ||
      ""
    );
  }

  getUserProfile(): Observable<User | null> {
    return of({ id: "me", email: "yourself@lepton.ai", enable: true });
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
    const url = import.meta.env.VITE_CLUSTER_URL || window.location.origin;
    const token = this.getTokenMapFromStorage();
    return of([{ url, token }]);
  }

  logout(): Promise<void> {
    this.storageService.set(StorageService.GLOBAL_SCOPE, "CLUSTER_TOKEN", "");
    return Promise.resolve(undefined);
  }
}
