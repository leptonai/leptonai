import { Injectable } from "injection-js";
import { ReplaySubject } from "rxjs";

@Injectable()
export class TitleService {
  title$ = new ReplaySubject<string>(1);
  setTitle(title: string, ogImageTitle = false) {
    const ogTitle = document.querySelector("meta[property='og:title']");
    const ogImage = document.querySelector("meta[property='og:image']");
    const twitterTitle = document.querySelector("meta[name='twitter:title']");
    document.title = `${title} | Lepton AI`;
    if (ogTitle) {
      ogTitle.setAttribute("content", `${title} | Lepton AI`);
    }
    if (twitterTitle) {
      twitterTitle.setAttribute("content", `${title} | Lepton AI`);
    }
    if (ogImage) {
      const ogImageURL = new URL("https://www.lepton.ai/api/og");
      if (ogImageTitle) {
        ogImageURL.searchParams.set("title", title);
      }
      ogImage.setAttribute("content", ogImageURL.toString());
    }

    this.title$.next(title);
  }
}
