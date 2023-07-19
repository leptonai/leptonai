import { Injectable } from "injection-js";
import { ReplaySubject } from "rxjs";

@Injectable()
export class TitleService {
  title$ = new ReplaySubject<string>(1);
  setTitle(title: string) {
    const ogTitle = document.querySelector("meta[property='og:title']");
    const twitterTitle = document.querySelector("meta[name='twitter:title']");
    document.title = `${title} | Lepton AI`;
    if (ogTitle) {
      ogTitle.setAttribute("content", `${title} | Lepton AI`);
    }
    if (twitterTitle) {
      twitterTitle.setAttribute("content", `${title} | Lepton AI`);
    }
    this.title$.next(title);
  }
}
