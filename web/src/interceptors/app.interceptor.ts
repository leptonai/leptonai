import { Injectable } from "injection-js";
import {
  HttpHandler,
  HTTPInterceptor,
  Request,
  Response,
} from "@lepton-dashboard/services/http-client.service";
import { catchError, mergeMap, Observable, throwError } from "rxjs";
import {
  AuthService,
  UnauthorizedError,
} from "@lepton-dashboard/services/auth.service";
import { NavigateService } from "@lepton-dashboard/services/navigate.service";
import { fromPromise } from "rxjs/internal/observable/innerFrom";
import { ProfileService } from "@lepton-dashboard/services/profile.service";

@Injectable()
export class AppInterceptor implements HTTPInterceptor {
  constructor(
    private navigateService: NavigateService,
    private profileService: ProfileService,
    private authService: AuthService
  ) {}

  intercept(req: Request, next: HttpHandler): Observable<Response> {
    const reqHost = new URL(req.url!).host;
    const token = this.profileService.profile?.authorized_clusters.find(
      (cluster) => new URL(cluster.auth.url).host === reqHost
    )?.auth.token;

    const headers = token
      ? { ...req.headers, Authorization: `Bearer ${token}` }
      : req.headers;

    return next
      .handle({
        ...req,
        headers,
      })
      .pipe(
        catchError((err) => {
          console.error(err);
          if (err.status === 401 || err.response?.status === 401) {
            return fromPromise(
              this.authService.logout().then(() => {
                this.navigateService.navigateTo("/login");
              })
            ).pipe(
              mergeMap(() =>
                throwError(() => new UnauthorizedError("Unauthorized"))
              )
            );
          }
          return throwError(err);
        })
      );
  }
}
