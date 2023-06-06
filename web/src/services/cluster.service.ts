import { Injectable } from "injection-js";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { Observable, tap } from "rxjs";
import { Cluster } from "@lepton-dashboard/interfaces/cluster";
import { ApiService } from "@lepton-dashboard/services/api.service";

export interface AuthenticatedCluster {
  id: string;
  url: string;
  token: string;
}

@Injectable()
export class ClusterService {
  currentCluster: Cluster | null = null;
  constructor(
    private authService: AuthService,
    private apiService: ApiService
  ) {}

  enabled(): Observable<boolean> {
    const abort = new AbortController();
    return new Observable<boolean>((subscriber) => {
      this.queryEnabled(abort)
        .then((d) => subscriber.next(d))
        .catch((e) => subscriber.error(e));
      return () => abort.abort();
    });
  }

  listClusters(): Observable<AuthenticatedCluster[]> {
    const abort = new AbortController();
    return new Observable<AuthenticatedCluster[]>((subscriber) => {
      this.queryClusters(abort)
        .then((d) => subscriber.next(d))
        .catch((e) => subscriber.error(e));
      return () => abort.abort();
    });
  }

  getCurrentClusterInfo(): Observable<Cluster> {
    return this.apiService
      .getClusterInfo()
      .pipe(tap((d) => (this.currentCluster = d)));
  }

  private async queryEnabled(abort = new AbortController()): Promise<boolean> {
    const { data: users, error } = await this.authService.client
      .from("users")
      .select("email, enable")
      .eq(
        "email",
        (
          await this.authService.client.auth.getUser()
        ).data.user?.email
      )
      .abortSignal(abort.signal);

    if (error) {
      throw error;
    }

    if (!users?.length) {
      return false;
    }

    return !!users[0].enable;
  }

  private async queryClusters(
    abort = new AbortController()
  ): Promise<AuthenticatedCluster[]> {
    const { data: clusters, error } = await this.authService.client
      .from("user_cluster")
      .select(
        `
      cluster_id,
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
          id: cluster.cluster_id,
          url: Array.isArray(cluster.clusters)
            ? cluster.clusters[0].url
            : cluster.clusters?.url,
          token: cluster.token,
        };
      })
      .filter((cluster): cluster is AuthenticatedCluster => !!cluster.url);
  }
}
