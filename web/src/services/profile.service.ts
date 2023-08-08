import { Injectable } from "injection-js";
import { catchError, forkJoin, map, Observable, of, tap } from "rxjs";
import { Profile } from "@lepton-dashboard/interfaces/profile";
import { AuthService } from "@lepton-dashboard/services/auth.service";

@Injectable()
export class ProfileService {
  profile: Profile | null = null;
  bootstrap(): Observable<boolean> {
    return forkJoin([
      this.authService.getUser().pipe(catchError(() => of(null))),
      this.authService.listAuthorizedWorkspaces().pipe(
        map((workspaces) =>
          workspaces.map((data) => ({
            auth: data,
            isBillingSupported: !!data.status,
            isPastDue: data.status === "past_due",
          }))
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

  constructor(private authService: AuthService) {}
}
