import { Injectable } from "injection-js";
import {
  debounceTime,
  EMPTY,
  fromEvent,
  interval,
  map,
  merge,
  shareReplay,
  startWith,
  Subject,
  switchMap,
} from "rxjs";
import { NavigateService } from "@lepton-dashboard/services/navigate.service";

@Injectable()
export class RefreshService {
  private interval$ = interval(10000).pipe(
    map(() => true),
    startWith(true)
  );

  private readonly manual$ = new Subject<boolean>();

  private readonly visibility$ = fromEvent(window, "visibilitychange").pipe(
    map((e) => !(e.target as Document).hidden)
  );

  constructor(private navigateService: NavigateService) {}

  public refresh(): void {
    this.manual$.next(true);
  }

  public refresh$ = merge(
    this.visibility$,
    this.manual$,
    this.navigateService.onNavigated().pipe(map(() => true))
  ).pipe(
    startWith(true),
    debounceTime(300),
    switchMap((active) => (active ? this.interval$ : EMPTY)),
    debounceTime(300),
    shareReplay(1)
  );
}
