import { Injectable } from "injection-js";
import {
  debounceTime,
  EMPTY,
  fromEvent,
  interval,
  map,
  merge,
  share,
  startWith,
  Subject,
  switchMap,
} from "rxjs";

@Injectable()
export class RefreshService {
  private interval$ = interval(10000).pipe(
    map(() => true),
    startWith(true)
  );

  private readonly manual$ = new Subject<boolean>();
  private readonly navigation$ = new Subject<string>();

  private readonly visibility$ = fromEvent(window, "visibilitychange").pipe(
    map((e) => !(e.target as Document).hidden)
  );

  public refresh(): void {
    this.manual$.next(true);
  }

  public integrateWithRouter(pathname: string): void {
    this.navigation$.next(pathname);
  }

  public refresh$ = merge(
    this.visibility$,
    this.manual$,
    this.navigation$.pipe(map(() => true))
  ).pipe(
    startWith(true),
    debounceTime(300),
    switchMap((active) => (active ? this.interval$ : EMPTY)),
    debounceTime(300),
    share()
  );
}
