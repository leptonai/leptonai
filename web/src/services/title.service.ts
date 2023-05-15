import { Injectable } from "injection-js";
import { ReplaySubject } from "rxjs";

@Injectable()
export class TitleService {
  title$ = new ReplaySubject<string>(1);
  setTitle(title: string) {
    document.title = `${title} | Lepton AI`;
    this.title$.next(title);
  }
}
