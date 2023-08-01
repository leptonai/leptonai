import { Injectable } from "injection-js";
import { EMPTY, Observable } from "rxjs";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { AuthorizedWorkspace } from "@lepton-dashboard/interfaces/workspace";
import { User, WaitlistEntry } from "@lepton-dashboard/interfaces/user";
import {
  HttpClientService,
  HttpContext,
} from "@lepton-dashboard/services/http-client.service";
import { INTERCEPTOR_CONTEXT } from "@lepton-dashboard/interceptors/app.interceptor.context";

@Injectable()
export class AuthPortalService implements AuthService {
  readonly authServerUrl =
    import.meta.env.VITE_PORTAL_URL || "http://localhost:8000";

  constructor(private http: HttpClientService) {}

  logout() {
    window.location.href = `${this.authServerUrl}/api/auth/logout?next=${window.location.origin}`;
    return EMPTY;
  }

  getUser(): Observable<User | null> {
    return this.http.get(`${this.authServerUrl}/api/auth/user`, {
      withCredentials: true,
      context: new HttpContext().set(INTERCEPTOR_CONTEXT, {
        ignoreErrors: [401],
      }),
    });
  }

  listAuthorizedWorkspaces(): Observable<AuthorizedWorkspace[]> {
    return this.http.get<AuthorizedWorkspace[]>(
      `${this.authServerUrl}/api/auth/workspaces`,
      {
        withCredentials: true,
      }
    );
  }

  joinWaitlist(entry: WaitlistEntry): Observable<void> {
    return this.http.post<void>(
      `${this.authServerUrl}/api/auth/waitlist`,
      entry,
      {
        withCredentials: true,
      }
    );
  }
}
