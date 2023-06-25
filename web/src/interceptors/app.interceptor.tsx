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
import { ReactNode } from "react";
import { NotificationService } from "@lepton-dashboard/services/notification.service";
import { INTERCEPTOR_CONTEXT } from "@lepton-dashboard/interceptors/app.interceptor.context";

@Injectable()
export class AppInterceptor implements HTTPInterceptor {
  constructor(
    private navigateService: NavigateService,
    private notificationService: NotificationService,
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
        catchError((error) => {
          console.error(error);

          if (req.context?.get(INTERCEPTOR_CONTEXT).ignoreErrors) {
            return throwError(error);
          }

          if (error.status === 401 || error.response?.status === 401) {
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

          const requestId = error.response?.headers?.["x-request-id"];
          const message: ReactNode = error.response?.data?.code || error.code;
          let description: ReactNode =
            error.response?.data?.message || error.message;
          description = requestId ? (
            <>
              <strong>Error Message</strong>: {description}
              <br />
              <strong>Request ID</strong>: {requestId}
              <br />
              <strong>Timestamp</strong>: {new Date().toLocaleString()}
            </>
          ) : (
            description
          );

          this.notificationService.error({
            message,
            description,
          });

          return throwError(error);
        })
      );
  }
}
