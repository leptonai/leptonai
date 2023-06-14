import { Injectable } from "injection-js";
import { catchError, forkJoin, map, mergeMap, Observable, of, tap } from "rxjs";
import { Profile } from "@lepton-dashboard/interfaces/profile";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { HttpClientService } from "./http-client.service";
import { Cluster, ClusterDetail } from "@lepton-dashboard/interfaces/cluster";

@Injectable()
export class ProfileService {
  profile: Profile | null = null;
  bootstrap(): Observable<boolean> {
    return forkJoin([
      this.authService.getSessionProfile().pipe(catchError(() => of(null))),
      this.authService.getUserProfile().pipe(catchError(() => of(null))),
      this.authService.listAuthorizedClusters().pipe(
        mergeMap((authClusters) =>
          authClusters.length > 0
            ? forkJoin([
                ...authClusters.map(({ url }) =>
                  this.httpClientService
                    .get<ClusterDetail>(`${url}/api/v1/cluster`)
                    .pipe(catchError(() => of(null)))
                ),
              ]).pipe(
                map((detailClusters) => {
                  return detailClusters
                    .map((data, i) => {
                      return {
                        auth: authClusters[i],
                        data,
                      };
                    })
                    .filter((c): c is Cluster => !!c.data);
                })
              )
            : of([])
        ),
        catchError(() => of([]))
      ),
    ]).pipe(
      tap(([auth_info, user, authorized_clusters]) => {
        this.profile = {
          identification: user,
          oauth: auth_info,
          authorized_clusters,
        };
      }),
      map(() => true)
    );
  }

  constructor(
    private authService: AuthService,
    private httpClientService: HttpClientService
  ) {}
}
