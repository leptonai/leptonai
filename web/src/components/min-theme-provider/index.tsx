import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { FC, PropsWithChildren } from "react";

export const MinThemeProvider: FC<PropsWithChildren> = ({ children }) => {
  return (
    <ThemeProvider
      token={{
        fontSize: 12,
        paddingXS: 6,
        colorBorderSecondary: "transparent",
      }}
    >
      {children}
    </ThemeProvider>
  );
};
