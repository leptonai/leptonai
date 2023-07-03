import { Injectable } from "injection-js";
import { createClient, Session } from "@supabase/supabase-js";
import { Database } from "@lepton-dashboard/interfaces/database";
import { BehaviorSubject, from, map, Observable } from "rxjs";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { AuthorizedWorkspace } from "@lepton-dashboard/interfaces/workspace";
import { User } from "@lepton-dashboard/interfaces/user";

/**
 * Must be instantiated outside OauthService
 */
const client = createClient<Database>(
  import.meta.env.VITE_SUPABASE_URL || "http://localhost:54321",
  import.meta.env.VITE_SUPABASE_KEY || "invalid"
);

@Injectable()
export class AuthSupabaseService implements AuthService {
  private session$ = new BehaviorSubject<Session | null>(null);
  public readonly client = client;

  constructor() {
    this.client.auth.getSession().then(({ data: { session } }) => {
      this.session$.next(session);
    });

    this.client.auth.onAuthStateChange((_event, session) => {
      this.session$.next(session);
    });
  }

  logout() {
    return this.client.auth.signOut().then(() => {
      this.session$.next(null);
    });
  }

  getSessionProfile(): Observable<Session["user"] | null> {
    return from(this.client.auth.getSession()).pipe(
      map(({ data }) => data.session?.user || null)
    );
  }

  getUserProfile(): Observable<User | null> {
    return new Observable((subscriber) => {
      const abort = new AbortController();
      this.selectUserProfile(abort)
        .then((d) => {
          subscriber.next(d);
          subscriber.complete();
        })
        .catch((e) => subscriber.error(e));
      return () => abort.abort();
    });
  }

  listAuthorizedWorkspaces(): Observable<AuthorizedWorkspace[]> {
    return new Observable<AuthorizedWorkspace[]>((subscriber) => {
      const abort = new AbortController();
      this.selectWorkspace(abort)
        .then((d) => {
          subscriber.next(d);
          subscriber.complete();
        })
        .catch((e) => subscriber.error(e));
      return () => {
        abort.abort();
      };
    });
  }

  private async selectUserProfile(
    abort: AbortController
  ): Promise<User | null> {
    const { data: users, error } = await this.client
      .from("users")
      .select("id, email, enable")
      .eq("email", (await this.client.auth.getUser()).data.user?.email)
      .abortSignal(abort.signal);

    if (error) {
      throw error;
    }

    return users[0] || null;
  }

  private async selectWorkspace(
    abort: AbortController
  ): Promise<AuthorizedWorkspace[]> {
    const { data: workspaces, error } = await this.client
      .from("user_workspace")
      .select(
        `
      token,
      workspaces(workspace_id: id, url)
    `
      )
      .abortSignal(abort.signal);

    if (error) {
      throw error;
    }

    return (workspaces || [])
      .map((workspace) => {
        return {
          url: Array.isArray(workspace.workspaces)
            ? workspace.workspaces[0].url
            : workspace.workspaces?.url,
          token: workspace.token,
        };
      })
      .filter((workspace): workspace is AuthorizedWorkspace => !!workspace.url);
  }
}
