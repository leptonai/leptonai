import { Injectable } from "injection-js";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { EMPTY, Observable, of } from "rxjs";
import { AuthorizedWorkspace } from "@lepton-dashboard/interfaces/workspace";
import { User } from "@lepton-dashboard/interfaces/user";
import { StorageService } from "@lepton-dashboard/services/storage.service";

@Injectable()
export class AuthTokenService implements AuthService {
  constructor(private storageService: StorageService) {}

  private getTokenMapFromStorage(): string {
    return (
      this.storageService.get(StorageService.GLOBAL_SCOPE, "WORKSPACE_TOKEN") ||
      ""
    );
  }

  getUser(): Observable<User | null> {
    return of({ id: "me", email: "yourself@lepton.ai", enable: true });
  }

  listAuthorizedWorkspaces(): Observable<AuthorizedWorkspace[]> {
    const url = new URL(
      import.meta.env.VITE_WORKSPACE_URL || window.location.origin
    );
    const token = this.getTokenMapFromStorage();
    const id = url.hostname.split(".")[0];
    return of([
      {
        url: url.toString(),
        token,
        id,
        displayName: id,
        status: "",
        paymentMethodAttached: false,
        tier: "Basic",
      },
    ]);
  }

  logout(): Observable<void> {
    this.storageService.set(StorageService.GLOBAL_SCOPE, "WORKSPACE_TOKEN", "");
    return of(void 0);
  }

  joinWaitlist(): Observable<void> {
    return EMPTY;
  }
}
