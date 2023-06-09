import { Injectable } from "injection-js";
import { createClient, Session } from "@supabase/supabase-js";
import { Database } from "@lepton-dashboard/interfaces/database";
import { BehaviorSubject, from, map, Observable } from "rxjs";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { AuthorizedCluster } from "@lepton-dashboard/interfaces/cluster";
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

  listAuthorizedClusters(): Observable<AuthorizedCluster[]> {
    return new Observable<AuthorizedCluster[]>((subscriber) => {
      const abort = new AbortController();
      this.selectClusters(abort)
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

  private async selectClusters(
    abort: AbortController
  ): Promise<AuthorizedCluster[]> {
    const { data: clusters, error } = await this.client
      .from("user_cluster")
      .select(
        `
      token,
      clusters(cluster_id: id, url)
    `
      )
      .abortSignal(abort.signal);

    if (error) {
      throw error;
    }

    return (clusters || [])
      .map((cluster) => {
        return {
          url: Array.isArray(cluster.clusters)
            ? cluster.clusters[0].url
            : cluster.clusters?.url,
          token: cluster.token,
        };
      })
      .filter((cluster): cluster is AuthorizedCluster => !!cluster.url);
  }
}
