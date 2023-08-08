import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { FC, PropsWithChildren } from "react";

export const MinThemeProvider: FC<PropsWithChildren> = ({ children }) => {
  const theme = useAntdTheme();
  return (
    <ThemeProvider
      token={{
        fontSize: 12,
        paddingXS: 6,
        colorBorderSecondary: "transparent",
        colorBorder: theme.colorBorderSecondary,
      }}
    >
      {children}
    </ThemeProvider>
  );
};
