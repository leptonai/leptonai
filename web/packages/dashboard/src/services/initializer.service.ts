import { Injectable } from "injection-js";
import { BehaviorSubject, tap } from "rxjs";
import { ProfileService } from "@lepton-dashboard/services/profile.service";

@Injectable()
export class InitializerService {
  initialized$ = new BehaviorSubject(false);
  bootstrap() {
    this.profileService
      .bootstrap()
      .pipe(tap(() => this.initialized$.next(true)))
      .subscribe();
  }

  constructor(private profileService: ProfileService) {}
}
