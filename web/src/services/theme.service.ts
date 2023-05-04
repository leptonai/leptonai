import { Injectable } from "injection-js";
import { BehaviorSubject } from "rxjs";
import { theme, ThemeConfig } from "antd";

@Injectable()
export class ThemeService {
  readonly shareToken: ThemeConfig["token"] = {
    borderRadius: 2,
    controlOutlineWidth: 0,
  };

  readonly presetThemes: { [key: string]: ThemeConfig } = {
    default: {
      token: {
        ...this.shareToken,
        colorPrimary: "#000",
        boxShadowTertiary:
          "0 1px 2px 0 rgba(0, 0, 0, 0.03),0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px 0 rgba(0, 0, 0, 0.02)",
      },
      algorithm: theme.defaultAlgorithm,
    },
    dark: {
      token: {
        ...this.shareToken,
        colorPrimary: "#fff",
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
