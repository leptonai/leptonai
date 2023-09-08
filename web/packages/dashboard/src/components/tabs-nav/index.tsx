import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { FC, ReactNode, useMemo } from "react";
import { Tabs } from "antd";
import { useLocation, useNavigate } from "react-router-dom";
import { css } from "@emotion/react";
import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props";

export const TabsNav: FC<
  {
    menuItems: Array<{ label: ReactNode; key: string; prefix?: string }>;
    keyActive?: (key: string) => void;
  } & EmotionProps
> = ({ menuItems, keyActive, className }) => {
  const theme = useAntdTheme();
  const location = useLocation();
  const selectedKey = useMemo(() => {
    return (
      menuItems.find((item) =>
        location.pathname.startsWith(`${item?.prefix || item?.key}`)
      )?.key || "$$never_match_key"
    );
  }, [location.pathname, menuItems]);
  const navigate = useNavigate();

  const navigateTo = useMemo(
    () => (key: string) => {
      keyActive && keyActive(key);
      navigate(key, { relative: "route" });
    },
    [keyActive, navigate]
  );
  return (
    <Tabs
      className={className}
      css={css`
        .ant-tabs-tab {
          user-select: none;
          padding: 9px 0 !important;
          &:hover .ant-tabs-tab-btn {
            background: ${theme.colorBgTextHover};
            border-radius: ${theme.borderRadius}px;
          }
        }
        .ant-tabs-tab-btn {
          padding: 3px 8px;
        }
        .ant-tabs-nav {
          margin-bottom: 0;
        }
        .ant-tabs-nav::before {
          display: none;
        }
        .ant-tabs-nav-operations {
          display: none !important;
        }
      `}
      moreIcon={null}
      tabBarGutter={12}
      tabBarStyle={{ marginBottom: 0 }}
      activeKey={selectedKey}
      items={menuItems}
      animated={false}
      onTabClick={(key) => navigateTo(key)}
    />
  );
};
