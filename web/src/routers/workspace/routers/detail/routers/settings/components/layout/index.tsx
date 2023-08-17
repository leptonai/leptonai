import {
  Asterisk,
  ContainerRegistry,
  Password,
  Settings,
  Wallet,
} from "@carbon/icons-react";
import { css } from "@emotion/react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ThemeProvider } from "@lepton-dashboard/components/theme-provider";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Card } from "@lepton-dashboard/components/card";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { useResponsive } from "ahooks";
import { Menu, MenuProps } from "antd";
import { FC, PropsWithChildren, useMemo } from "react";
import { useLocation, useNavigate, useResolvedPath } from "react-router-dom";
import { ImagePullSecretService } from "@lepton-dashboard/routers/workspace/services/image-pull-secret.service";
import { useStateFromBehaviorSubject } from "@lepton-libs/hooks/use-state-from-observable";

export const Layout: FC<PropsWithChildren> = ({ children }) => {
  const theme = useAntdTheme();
  const responsive = useResponsive();
  const location = useLocation();
  const { pathname } = useResolvedPath("");
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const imagePullSecretService = useInject(ImagePullSecretService);
  const registryAvailable = useStateFromBehaviorSubject(
    imagePullSecretService.available$
  );
  const menuItems: MenuProps["items"] = useMemo(() => {
    const menus = [
      {
        key: `${pathname}/general`,
        label: "General",
        icon: <CarbonIcon icon={<Settings />} />,
      },
      {
        key: `${pathname}/api-tokens`,
        label: "API tokens",
        icon: <CarbonIcon icon={<Password />} />,
      },
      {
        key: `${pathname}/secrets`,
        label: "Secrets",
        icon: <CarbonIcon icon={<Asterisk />} />,
      },
      {
        key: `${pathname}/registries`,
        label: "Registries",
        icon: <CarbonIcon icon={<ContainerRegistry />} />,
        disabled: !registryAvailable,
      },
    ];
    if (workspaceTrackerService?.workspace?.isBillingSupported) {
      menus.push({
        key: `${pathname}/billing`,
        label: "Billing",
        icon: <CarbonIcon icon={<Wallet />} />,
      });
    }
    return menus.filter((item) => !item.disabled);
  }, [
    pathname,
    registryAvailable,
    workspaceTrackerService?.workspace?.isBillingSupported,
  ]);
  const selectedKeys: string[] = useMemo(() => {
    return menuItems
      .filter((item) => location.pathname.startsWith(`${item?.key}`))
      .map((item) => item!.key as string);
  }, [location.pathname, menuItems]);

  const navigate = useNavigate();

  const navigateTo = useMemo(
    () => (key: string) => {
      navigate(key, { relative: "route" });
    },
    [navigate]
  );
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
          inset: 16px 8px;
          display: flex;
        `}
      >
        <div
          css={css`
            height: 100%;
            padding-right: 8px;
            flex: 0 0 auto;
            border-right: 1px solid ${theme.colorBorder};
          `}
        >
          <ThemeProvider
            token={{
              controlHeightLG: 32,
              lineWidth: 0,
            }}
          >
            <Menu
              css={css`
                .ant-menu-item-selected {
                  overflow: visible;
                }
                .ant-menu-item-selected::before {
                  content: "";
                  width: 3px;
                  height: 100%;
                  position: absolute;
                  left: -2px;
                  background: ${theme.colorText};
                }
              `}
              inlineIndent={12}
              inlineCollapsed={!responsive["sm"]}
              onClick={({ key }) => navigateTo(key as string)}
              mode="inline"
              selectedKeys={selectedKeys}
              items={menuItems}
            />
          </ThemeProvider>
        </div>
        <div
          css={css`
            flex: 1 1 auto;
            padding: 0 8px;
            overflow: auto;
          `}
        >
          {children}
        </div>
      </div>
    </Card>
  );
};
