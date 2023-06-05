import { Injectable } from "injection-js";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { from, Observable } from "rxjs";

export interface AuthenticatedCluster {
  id: string;
  url: string;
  token: string;
}

@Injectable()
export class ClusterService {
  constructor(private authService: AuthService) {}

  enabled(): Observable<boolean> {
    return from(this.queryEnabled());
  }

  listClusters(): Observable<AuthenticatedCluster[]> {
    return from(this.queryClusters());
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
