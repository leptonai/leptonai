import { FC, useMemo } from "react";
import { Tabs, TabsProps } from "antd";
import { useLocation, useNavigate } from "react-router-dom";

export const TabsNav: FC<{
  menuItems: NonNullable<TabsProps["items"]>;
  keyActive?: (key: string) => void;
}> = ({ menuItems, keyActive }) => {
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
      moreIcon={null}
      tabBarGutter={32}
      tabBarStyle={{ marginBottom: 0 }}
      activeKey={selectedKey}
      items={menuItems}
      onTabClick={(key) => navigateTo(key)}
    />
  );
};
