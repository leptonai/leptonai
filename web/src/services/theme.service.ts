import { Injectable } from "injection-js";
import { BehaviorSubject } from "rxjs";
import { theme, ThemeConfig } from "antd";

@Injectable()
export class ThemeService {
  readonly shareToken: ThemeConfig["token"] = {
    colorPrimary: "#2F80ED",
  };

  readonly presetThemes = {
    default: {
      token: {
        ...this.shareToken,
      },
      algorithm: theme.defaultAlgorithm,
    },
    dark: {
      token: {
        ...this.shareToken,
      },
      algorithm: theme.darkAlgorithm,
    },
  };

  public theme$ = new BehaviorSubject<ThemeConfig>(this.presetThemes.default);

  toggleTheme() {
    this.theme$.getValue() === this.presetThemes.default
      ? this.theme$.next(this.presetThemes.dark)
      : this.theme$.next(this.presetThemes.default);
  }
}
