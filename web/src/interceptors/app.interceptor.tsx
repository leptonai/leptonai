import { TrackerService } from "@lepton-dashboard/services/tracker.service";
import { Injectable } from "injection-js";
import {
  HttpHandler,
  HTTPInterceptor,
  HTTPRequest,
  HTTPResponse,
} from "@lepton-dashboard/services/http-client.service";
import { catchError, mergeMap, Observable, tap, throwError } from "rxjs";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { NavigateService } from "@lepton-dashboard/services/navigate.service";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { ReactNode } from "react";
import { NotificationService } from "@lepton-dashboard/services/notification.service";
import { INTERCEPTOR_CONTEXT } from "@lepton-dashboard/interceptors/app.interceptor.context";
import { UnauthorizedError } from "@lepton-libs/erroes/unauthorized";

@Injectable()
export class AppInterceptor implements HTTPInterceptor {
  constructor(
    private navigateService: NavigateService,
    private eventTrackerService: TrackerService,
    private notificationService: NotificationService,
    private profileService: ProfileService,
    private authService: AuthService
  ) {}

  intercept(req: HTTPRequest, next: HttpHandler): Observable<HTTPResponse> {
    const reqHost = new URL(req.url!).host;
    const token = this.profileService.profile?.authorized_workspaces.find(
      (workspace) => new URL(workspace.auth.url).host === reqHost
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
          const status = error.status || error.response?.status;
          const ignoreErrors =
            req.context?.get(INTERCEPTOR_CONTEXT).ignoreErrors;

          const requestId = error.response?.headers?.["x-request-id"];
          const message: ReactNode = error.response?.data?.code || error.code;
          const errorMessage = error.response?.data?.message || error.message;
          const time = new Date();

          const ignore401 =
            Array.isArray(ignoreErrors) && ignoreErrors.includes(401);

          // request to ignore 401 errors explicitly
          if (status === 401 && !ignore401) {
            return this.authService.logout().pipe(
              tap(() => {
                this.navigateService.navigateTo("login");
              }),
              mergeMap(() =>
                throwError(() => new UnauthorizedError("Unauthorized"))
              )
            );
          }

          if (
            ignoreErrors === true ||
            (Array.isArray(ignoreErrors) && ignoreErrors.includes(status))
          ) {
            return throwError(() => error);
          }

          this.eventTrackerService.error(error, "API_ERROR", {
            requestId,
            errorMessage,
            body: req.data,
            timestamp: time.toUTCString(),
          });

          const description = requestId ? (
            <>
              <strong>Error Message</strong>: {errorMessage}
              <br />
              <strong>Request ID</strong>: {requestId}
              <br />
              <strong>Timestamp</strong>: {time.toLocaleString()}
            </>
          ) : (
            errorMessage
          );

          this.notificationService.error({
            message,
            description,
          });

          return throwError(() => error);
        })
      );
  }
}
