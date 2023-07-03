import { Injectable } from "injection-js";
import { Session, SupabaseClient } from "@supabase/supabase-js";
import { Observable } from "rxjs";
import { AuthorizedWorkspace } from "@lepton-dashboard/interfaces/workspace";
import { User } from "@lepton-dashboard/interfaces/user";

export class UnauthorizedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "UnauthorizedError";
  }
}

export type WaitlistEntry = Pick<
  User,
  "company" | "companySize" | "industry" | "role" | "name"
>;

@Injectable()
export abstract class AuthService {
  public readonly client: SupabaseClient | null = null;
  abstract getUserProfile(): Observable<User | null>;
  abstract getSessionProfile(): Observable<Session["user"] | null>;
  abstract listAuthorizedWorkspaces(): Observable<AuthorizedWorkspace[]>;
  abstract logout(): Promise<void>;
  abstract joinWaitlist(entry: WaitlistEntry): Observable<void>;
}
