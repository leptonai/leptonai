import { Injectable } from "injection-js";
import { ReplaySubject } from "rxjs";

@Injectable()
export class MetaService {
  title$ = new ReplaySubject<string>(1);
  setTitle(title: string, setToImage = false) {
    const ogTitle = document.querySelector("meta[property='og:title']");
    const ogImage = document.querySelector("meta[property='og:image']");
    const twitterTitle = document.querySelector("meta[name='twitter:title']");
    const twitterImage = document.querySelector("meta[name='twitter:image']");
    const ogImageURL = new URL("https://www.lepton.ai/api/og");
    document.title = `${title} | Lepton AI`;

    if (setToImage) {
      ogImageURL.searchParams.set("title", title);
    }

    if (ogTitle) {
      ogTitle.setAttribute("content", `${title} | Lepton AI`);
    }
    if (twitterTitle) {
      twitterTitle.setAttribute("content", `${title} | Lepton AI`);
    }

    if (ogImage) {
      ogImage.setAttribute("content", ogImageURL.toString());
    }
    if (twitterImage) {
      twitterImage.setAttribute("content", ogImageURL.toString());
    }

    this.title$.next(title);
  }

  setURLPath(urlPath?: string) {
    // Only available on production
    const url = new URL("https://dashboard.lepton.ai/");
    url.pathname = urlPath ?? window.location.pathname;
    const ogURL = document.querySelector("meta[property='og:url']");
    if (ogURL) {
      ogURL.setAttribute("content", url.toString());
    }
  }
}