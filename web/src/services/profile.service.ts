import { Injectable } from "injection-js";
import {
  catchError,
  forkJoin,
  map,
  mergeMap,
  Observable,
  of,
  retry,
  tap,
} from "rxjs";
import { Profile } from "@lepton-dashboard/interfaces/profile";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { HttpClientService, HttpContext } from "./http-client.service";
import { WorkspaceDetail } from "@lepton-dashboard/interfaces/workspace";
import { INTERCEPTOR_CONTEXT } from "@lepton-dashboard/interceptors/app.interceptor.context";
import pathJoin from "@lepton-libs/url/path-join";

@Injectable()
export class ProfileService {
  profile: Profile | null = null;
  bootstrap(): Observable<boolean> {
    return forkJoin([
      this.authService.getUser().pipe(catchError(() => of(null))),
      this.authService.listAuthorizedWorkspaces().pipe(
        mergeMap((authWorkspaces) =>
          authWorkspaces.length > 0
            ? forkJoin([
                ...authWorkspaces.map(({ url, token }) => {
                  const apiUrl = pathJoin(url, "/api/v1/workspace");
                  return this.httpClientService
                    .get<WorkspaceDetail>(apiUrl, {
                      headers: {
                        // The interceptor will set the token from the profile to the header,
                        // but the token is not set to profile now, so we need to set it manually.
                        Authorization: `Bearer ${token}`,
                      },
                      context: new HttpContext().set(INTERCEPTOR_CONTEXT, {
                        ignoreErrors: true,
                      }),
                    })
                    .pipe(
                      retry({
                        count: 10,
                        delay: 1000,
                      }),
                      catchError(() => of(null))
                    );
                }),
              ]).pipe(
                map((detailWorkspaces) => {
                  return detailWorkspaces.map((data, i) => {
                    return {
                      auth: authWorkspaces[i],
                      data,
                      isBillingSupported: !!authWorkspaces[i].status,
                      isPastDue: authWorkspaces[i].status === "past_due",
                    };
                  });
                })
              )
            : of([])
        ),
        catchError(() => of([]))
      ),
    ]).pipe(
      tap(([user, authorized_workspaces]) => {
        this.profile = {
          identification: user,
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
