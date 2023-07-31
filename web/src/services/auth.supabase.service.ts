import { Injectable } from "injection-js";
import {
  createClient,
  Session,
  User as SessionUser,
} from "@supabase/supabase-js";
import { BehaviorSubject, from, Observable } from "rxjs";
import {
  AuthService,
  WaitlistEntry,
} from "@lepton-dashboard/services/auth.service";
import { AuthorizedWorkspace } from "@lepton-dashboard/interfaces/workspace";
import { User } from "@lepton-dashboard/interfaces/user";
import { Database } from "@lepton-dashboard/interfaces/database";
import {
  HttpClientService,
  HttpContext,
} from "@lepton-dashboard/services/http-client.service";
import { INTERCEPTOR_CONTEXT } from "@lepton-dashboard/interceptors/app.interceptor.context";

/**
 * Must be instantiated outside OauthService
 */
const client = createClient<Database>(
  import.meta.env.VITE_SUPABASE_URL || "http://localhost:54321",
  import.meta.env.VITE_SUPABASE_KEY || "invalid"
);

const SSO_CONFIG = {
  domain: window.location.hostname === "localhost" ? "localhost" : "lepton.ai",
  access_token_key: "lepton-access-token",
  refresh_token_key: "lepton-refresh-token",
};

@Injectable()
export class AuthSupabaseService implements AuthService {
  private session$ = new BehaviorSubject<Session | null>(null);
  public readonly client = client;

  constructor(private http: HttpClientService) {
    this.client.auth.getSession().then(({ data: { session } }) => {
      this.session$.next(session);
    });

    this.client.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_OUT") {
        // delete cookies on sign out
        const expires = new Date(0).toUTCString();
        document.cookie = `${SSO_CONFIG.access_token_key}=; Domain=${SSO_CONFIG.domain}; path=/; expires=${expires}; SameSite=Lax; secure`;
        document.cookie = `${SSO_CONFIG.refresh_token_key}=; Domain=${SSO_CONFIG.domain}}; path=/; expires=${expires}; SameSite=Lax; secure`;
      } else if (event === "SIGNED_IN" || event === "TOKEN_REFRESHED") {
        const maxAge = 100 * 365 * 24 * 60 * 60; // 100 years, never expires
        document.cookie = `${SSO_CONFIG.access_token_key}=${
          session!.access_token
        }; Domain=${
          SSO_CONFIG.domain
        }; path=/; max-age=${maxAge}; SameSite=Lax; secure`;
        document.cookie = `${SSO_CONFIG.refresh_token_key}=${
          session!.refresh_token
        }; Domain=${
          SSO_CONFIG.domain
        }; path=/; max-age=${maxAge}; SameSite=Lax; secure`;
      }
      this.session$.next(session);
    });
  }

  logout() {
    return this.client.auth.signOut().then(() => {
      this.session$.next(null);
    });
  }

  private async getSessionUser(): Promise<SessionUser | null> {
    const cookies = document.cookie
      .split(/\s*;\s*/)
      .map((cookie) => cookie.split("="));

    const accessTokenCookie = cookies.find(
      (x) => x[0] == `${SSO_CONFIG.access_token_key}`
    );
    const refreshTokenCookie = cookies.find(
      (x) => x[0] == `${SSO_CONFIG.refresh_token_key}`
    );

    const session = await this.client.auth.getSession();
    const user = session.data.session?.user;
    if (user) {
      return user;
    } else if (accessTokenCookie && refreshTokenCookie) {
      const beforeSession = await client.auth.setSession({
        access_token: accessTokenCookie[1],
        refresh_token: refreshTokenCookie[1],
      });
      return beforeSession.data.session?.user || null;
    } else {
      return null;
    }
  }

  getSessionProfile(): Observable<SessionUser | null> {
    this.http
      .get("https://portal.lepton.ai/api/auth/profile", {
        withCredentials: true,
        context: new HttpContext().set(INTERCEPTOR_CONTEXT, {
          ignoreErrors: [401],
        }),
      })
      .subscribe();
    return from(this.getSessionUser());
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

  joinWaitlist(entry: WaitlistEntry): Observable<void> {
    return new Observable((subscriber) => {
      const abort = new AbortController();
      this.updateWaitInfo(entry, abort)
        .then(() => {
          subscriber.next();
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
      .select("id, email, enable, name")
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
      workspaces(id, url, display_name, status)
    `
      )
      .abortSignal(abort.signal);

    if (error) {
      throw error;
    }

    return (workspaces || [])
      .map((workspace) => {
        const getFieldValue = <
          T extends "id" | "display_name" | "status" | "url"
        >(
          field: T
        ) => {
          const value = Array.isArray(workspace.workspaces)
            ? workspace.workspaces[0][field]
            : workspace.workspaces?.[field];
          return value ? value : "";
        };

        const id = getFieldValue("id");
        const displayName = getFieldValue("display_name");
        const status = getFieldValue("status");
        const url = getFieldValue("url");
        return {
          id,
          displayName,
          status,
          url,
          token: workspace.token,
        };
      })
      .filter((workspace): workspace is AuthorizedWorkspace => !!workspace.url);
  }

  private async updateWaitInfo(user: Partial<User>, abort: AbortController) {
    const { data, error } = await this.client
      .rpc("join_waitlist", {
        company: user.company || "",
        company_size: user.companySize || "",
        industry: user.industry || "",
        role: user.role || "",
        name: user.name || "",
        work_email: user.workEmail || "",
      })
      .abortSignal(abort.signal);

    if (error) {
      throw error;
    }

    return data;
  }
}
