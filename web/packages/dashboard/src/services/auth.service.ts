import { Injectable } from "injection-js";
import { Observable } from "rxjs";
import { AuthorizedWorkspace } from "@lepton-dashboard/interfaces/workspace";
import { User, WaitlistEntry } from "@lepton-dashboard/interfaces/user";

@Injectable()
export abstract class AuthService {
  abstract readonly authServerUrl?: string;
  abstract getUser(): Observable<User | null>;
  abstract listAuthorizedWorkspaces(): Observable<AuthorizedWorkspace[]>;
  abstract logout(): Observable<void>;
  abstract joinWaitlist(entry: WaitlistEntry): Observable<void>;
}
