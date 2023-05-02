import { FC, PropsWithChildren } from "react";
import { ConfigProvider } from "antd";
import { useInject } from "@lepton-libs/di";
import { ThemeService } from "@lepton-dashboard/services/theme.service.ts";
import { useStateFromBehaviorSubject } from "@lepton-libs/hooks/use-state-from-observable.ts";

export const ThemeProvider: FC<PropsWithChildren> = ({ children }) => {
  const themeService = useInject(ThemeService);
  const theme = useStateFromBehaviorSubject(themeService.theme$);
  return <ConfigProvider theme={theme}>{children}</ConfigProvider>;
};
