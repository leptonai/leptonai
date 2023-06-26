import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { FC, useMemo } from "react";
import { Tabs, TabsProps } from "antd";
import { useLocation, useNavigate } from "react-router-dom";
import { css } from "@emotion/react";
import { EmotionProps } from "@lepton-dashboard/interfaces/emotion-props";

export const TabsNav: FC<
  {
    menuItems: NonNullable<TabsProps["items"]>;
    keyActive?: (key: string) => void;
  } & EmotionProps
> = ({ menuItems, keyActive, className }) => {
  const theme = useAntdTheme();
  const location = useLocation();
  const selectedKey = useMemo(() => {
    return menuItems.find((item) =>
      location.pathname.startsWith(`${item?.key}`)
    )?.key;
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
      tabBarGutter={16}
      tabBarStyle={{ marginBottom: 0 }}
      activeKey={selectedKey}
      items={menuItems}
      animated={false}
      onTabClick={(key) => navigateTo(key)}
    />
  );
};
