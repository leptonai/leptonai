import { Injectable } from "injection-js";
import type { NavigateOptions, To } from "react-router-dom";
import { Observable, Subject } from "rxjs";

@Injectable()
export class NavigateService {
  private navigateTo$ = new Subject<[To, NavigateOptions?]>();
  private navigated$ = new Subject<string>();

  navigateTo(to: To, options?: NavigateOptions) {
    this.navigateTo$.next([to, options]);
  }

  onNavigate() {
    return this.navigateTo$.asObservable();
  }

  onNavigated(): Observable<string> {
    return this.navigated$.asObservable();
  }

  emitNavigated(pathname: string) {
    this.navigated$.next(pathname);
  }
}
