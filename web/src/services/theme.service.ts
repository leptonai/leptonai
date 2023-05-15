import { Injectable } from "injection-js";
import { BehaviorSubject } from "rxjs";
import { theme, ThemeConfig } from "antd";

@Injectable()
export class ThemeService {
  readonly shareToken: ThemeConfig["token"] = {
    borderRadius: 4,
    controlOutlineWidth: 0,
  };

  readonly presetThemes: { [key: string]: ThemeConfig } = {
    default: {
      token: {
        ...this.shareToken,
        colorPrimary: "#000",
        colorLink: "#000",
        colorLinkHover: "#555",
        colorLinkActive: "#333",
        controlItemBgActive: "#e6f4ff",
        boxShadowTertiary:
          "0 1px 2px 0 rgba(0, 0, 0, 0.03),0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px 0 rgba(0, 0, 0, 0.02)",
      },
      algorithm: theme.defaultAlgorithm,
      components: {
        Badge: {
          colorPrimary: "#2F80ED",
        },
        Notification: {
          width: 500,
          fontSize: 12,
        },
      },
    },
    dark: {
      token: {
        ...this.shareToken,
        controlItemBgActive: "#e6f4ff",
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
