import { css } from "@emotion/react";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Tag } from "antd";
import { ReactNode } from "react";

export const SmallTag = ({
  children,
  icon,
  color,
}: {
  children: ReactNode;
  icon?: ReactNode;
  color?: string;
}) => {
  const theme = useAntdTheme();
  return (
    <ThemeProvider
      token={{
        fontSize: 12,
        paddingXS: 6,
        colorBorderSecondary: "transparent",
      }}
    >
      <Tag
        icon={icon}
        color={color}
        css={css`
          margin-right: 0;
          color: ${theme.colorText};
        `}
      >
        {children}
      </Tag>
    </ThemeProvider>
  );
};
