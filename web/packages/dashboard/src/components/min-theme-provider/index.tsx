import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { FC, PropsWithChildren } from "react";

export const MinThemeProvider: FC<
  PropsWithChildren<{ hideBorder?: boolean }>
> = ({ children, hideBorder = true }) => {
  const theme = useAntdTheme();
  return (
    <ThemeProvider
      token={{
        fontSize: 12,
        paddingXS: 6,
        colorBorderSecondary: hideBorder
          ? "transparent"
          : theme.colorBorderSecondary,
      }}
    >
      {children}
    </ThemeProvider>
  );
};
