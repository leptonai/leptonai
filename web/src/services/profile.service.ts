import { Injectable } from "injection-js";
import { catchError, forkJoin, map, mergeMap, Observable, of, tap } from "rxjs";
import { Profile } from "@lepton-dashboard/interfaces/profile";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { HttpClientService, HttpContext } from "./http-client.service";
import { WorkspaceDetail } from "@lepton-dashboard/interfaces/workspace";
import { INTERCEPTOR_CONTEXT } from "@lepton-dashboard/interceptors/app.interceptor.context";

@Injectable()
export class ProfileService {
  profile: Profile | null = null;
  bootstrap(): Observable<boolean> {
    return forkJoin([
      this.authService.getSessionProfile().pipe(catchError(() => of(null))),
      this.authService.getUserProfile().pipe(catchError(() => of(null))),
      this.authService.listAuthorizedWorkspaces().pipe(
        mergeMap((authWorkspaces) =>
          authWorkspaces.length > 0
            ? forkJoin([
                ...authWorkspaces.map(({ url, token }) => {
                  return this.httpClientService
                    .get<WorkspaceDetail>(`${url}/api/v1/workspace`, {
                      headers: {
                        // The interceptor will set the token from the profile to the header,
                        // but the token is not set to profile now, so we need to set it manually.
                        Authorization: `Bearer ${token}`,
                      },
                      context: new HttpContext().set(INTERCEPTOR_CONTEXT, {
                        ignoreErrors: true,
                      }),
                    })
                    .pipe(catchError(() => of(null)));
                }),
              ]).pipe(
                map((detailWorkspaces) => {
                  return detailWorkspaces.map((data, i) => {
                    return {
                      auth: authWorkspaces[i],
                      data,
                    };
                  });
                })
              )
            : of([])
        ),
        catchError(() => of([]))
      ),
    ]).pipe(
      tap(([auth_info, user, authorized_workspaces]) => {
        this.profile = {
          identification: user,
          oauth: auth_info,
          authorized_workspaces,
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
