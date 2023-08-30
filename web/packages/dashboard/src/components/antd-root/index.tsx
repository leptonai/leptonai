import { css } from "@emotion/react";
import { App } from "antd";
import { FC, PropsWithChildren, useEffect } from "react";
import { useBrowserShiki } from "@lepton/ui/shared/shiki";
import { ThemeService } from "@lepton-dashboard/services/theme.service";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { map } from "rxjs";

export const AntdRoot: FC<PropsWithChildren> = ({ children }) => {
  const { setThemeMode, getHighlighter } = useBrowserShiki();
  const themeService = useInject(ThemeService);

  useStateFromObservable(
    () => themeService.theme$.pipe(map(() => themeService.getValidTheme())),
    themeService.getValidTheme(),
    {
      next: (theme) => {
        setThemeMode(theme === "dark" ? "dark" : "light");
      },
    }
  );

  useEffect(() => {
    // preload highlighter
    void getHighlighter();
  }, [getHighlighter]);

  return (
    <App
      notification={{ maxCount: 1 }}
      css={css`
        height: 100%;
      `}
    >
      {children}
    </App>
  );
};
