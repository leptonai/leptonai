import { Injectable } from "injection-js";
import { ReplaySubject } from "rxjs";
import { theme, ThemeConfig } from "antd";
import { StorageService } from "@lepton-dashboard/services/storage.service";

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
        colorPrimary: "#1F2328",
        colorLink: "#1F2328",
        colorBgLayout: "#f6f8fa",
        colorFillAlter: "#f6f8fa",
        colorBorder: "#d0d7de",
        colorLinkHover: "#555",
        colorLinkActive: "#333",
        controlItemBgActiveHover: "#f6f8fa",
        controlItemBgActive: "#f6f8fa",
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
        colorPrimary: "rgba(255, 255, 255, 0.5)",
        colorBgLayout: "#010409",
        colorBgElevated: "#161b22",
        colorBgContainer: "#0d1117",
        colorBorder: "hsla(0,0%,100%,.075)",
        colorLink: "#eee",
        colorLinkHover: "#555",
        colorPrimaryActive: "#555",
        colorPrimaryHover: "#555",
        colorLinkActive: "#333",
        controlItemBgActive: "#161b22",
        controlItemBgActiveHover: "#161b22",
      },
      components: {
        Tabs: {
          colorPrimaryHover: "#fff",
        },
        Button: {
          colorPrimary: "#21262d",
          colorPrimaryHover: "#30363d",
        },
        Badge: {
          colorPrimary: "#2F80ED",
        },
        Notification: {
          width: 500,
          fontSize: 12,
        },
      },
      algorithm: theme.darkAlgorithm,
    },
  };

  public theme$ = new ReplaySubject<ThemeConfig>(1);

  getValidTheme(): string {
    const themeIndex =
      this.storageService.get(StorageService.GLOBAL_SCOPE, "THEME") ||
      "default";
    const isValid = !!this.presetThemes[themeIndex];
    return isValid ? themeIndex : "default";
  }

  toggleTheme() {
    const reverseTheme =
      this.getValidTheme() === "default" ? "dark" : "default";
    this.storageService.set(StorageService.GLOBAL_SCOPE, "THEME", reverseTheme);
    this.theme$.next(this.presetThemes[reverseTheme]);
  }

  constructor(private storageService: StorageService) {
    this.theme$.next(this.presetThemes[this.getValidTheme()]);
  }
}
