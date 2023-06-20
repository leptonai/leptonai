import {
  Asterisk,
  Password,
  Settings,
  VolumeFileStorage,
} from "@carbon/icons-react";
import { css } from "@emotion/react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Card } from "@lepton-dashboard/routers/workspace/components/card";
import { Menu, MenuProps } from "antd";
import { FC, PropsWithChildren } from "react";

const menuItems: MenuProps["items"] = [
  {
    key: "general",
    label: "General",
    icon: <CarbonIcon icon={<Settings />} />,
  },
  {
    key: "api-tokens",
    label: "API tokens",
    icon: <CarbonIcon icon={<Password />} />,
  },
  {
    key: "secrets",
    label: "Secrets",
    icon: <CarbonIcon icon={<Asterisk />} />,
  },
  {
    key: "volumes",
    label: "Volumes",
    icon: <CarbonIcon icon={<VolumeFileStorage />} />,
  },
];

export const Layout: FC<PropsWithChildren> = ({ children }) => {
  const theme = useAntdTheme();
  return (
    <Card
      paddingless
      css={css`
        background: ${theme.colorBgContainer};
        flex: 1 1 auto;
      `}
    >
      <div
        css={css`
          position: absolute;
          inset: 16px;
          display: flex;
        `}
      >
        <div
          css={css`
            height: 100%;
            padding-right: 16px;
            flex: 0 0 200px;
            border-right: 1px solid ${theme.colorBorderSecondary};
          `}
        >
          <ThemeProvider
            token={{
              controlHeightLG: 32,
              lineWidth: 0,
              controlItemBgActive: theme.colorBgTextHover,
            }}
          >
            <Menu mode="vertical" items={menuItems} />
          </ThemeProvider>
        </div>
        <div
          css={css`
            flex: 1 1 auto;
            padding: 0 16px;
          `}
        >
          {children}
        </div>
      </div>
    </Card>
  );
};
