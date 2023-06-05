import { Injectable } from "injection-js";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { from, Observable, tap } from "rxjs";
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
    return from(this.queryEnabled());
  }

  listClusters(): Observable<AuthenticatedCluster[]> {
    return from(this.queryClusters());
  }

  getCurrentClusterInfo(): Observable<Cluster> {
    return this.apiService
      .getClusterInfo()
      .pipe(tap((d) => (this.currentCluster = d)));
  }

  private async queryEnabled(): Promise<boolean> {
    const { data: users, error } = await this.authService.client
      .from("users")
      .select("email, enable")
      .eq(
        "email",
        (
          await this.authService.client.auth.getUser()
        ).data.user?.email
      );

    if (error) {
      throw error;
    }

    if (!users?.length) {
      return false;
    }

    return !!users[0].enable;
  }

  private async queryClusters(): Promise<AuthenticatedCluster[]> {
    const { data: clusters, error } = await this.authService.client
      .from("clusters")
      .select(`id, token, url`);

    if (error) {
      throw error;
    }

    return (clusters || []).map((cluster) => ({
      id: cluster.id,
      url: cluster.url,
      token: cluster.token,
    }));
  }
}
