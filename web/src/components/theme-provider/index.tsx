import { FC, PropsWithChildren } from "react";
import { ConfigProvider } from "antd";
import { useInject } from "@lepton-libs/di";
import { ThemeService } from "@lepton-dashboard/services/theme.service.ts";
import { useStateFromBehaviorSubject } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { ThemeConfig } from "antd/es/config-provider/context";

export const ThemeProvider: FC<
  PropsWithChildren<{ token?: ThemeConfig["token"] }>
> = ({ children, token }) => {
  const themeService = useInject(ThemeService);
  const theme = useStateFromBehaviorSubject(themeService.theme$);
  const mergedTheme = token ? { ...theme, token } : theme;
  return <ConfigProvider theme={mergedTheme}>{children}</ConfigProvider>;
};
