import { css } from "@emotion/react";
import { MinThemeProvider } from "@lepton-dashboard/components/min-theme-provider";
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
  return (
    <MinThemeProvider>
      <Tag
        icon={icon}
        color={color}
        bordered={false}
        css={css`
          margin-inline: 0;
          cursor: default;
          font-weight: 500;
        `}
      >
        {children}
      </Tag>
    </MinThemeProvider>
  );
};
