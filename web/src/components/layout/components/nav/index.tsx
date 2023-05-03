import { Badge, Menu, MenuProps } from "antd";
import styled from "@emotion/styled";
import { FC, useMemo } from "react";
import {
  AppstoreOutlined,
  ExperimentOutlined,
  RocketOutlined,
} from "@ant-design/icons";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";
import { useLocation, useNavigate } from "react-router-dom";

const Container = styled.div`
  position: sticky;
  padding: 0 8px;
  z-index: 1;
  flex: 0 0 45px;
  top: 0;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03),
    0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px 0 rgba(0, 0, 0, 0.02);
`;
const StyledBadge = styled(Badge)`
  margin-left: 12px;
  top: -1px;
`;

const menuItems: MenuProps["items"] = [
  {
    label: <>Dashboard</>,
    key: "/dashboard",
    icon: <AppstoreOutlined />,
  },
  {
    label: (
      <>
        Models
        <StyledBadge size="small" color="#ccc" count={10} />
      </>
    ),
    key: "/models",
    icon: <ExperimentOutlined />,
  },
  {
    label: (
      <>
        Deployments
        <StyledBadge size="small" color="#ccc" count={32} />
      </>
    ),
    key: "/deployments",
    icon: <RocketOutlined />,
  },
];

export const Nav: FC = () => {
  const theme = useAntdTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const selectedKeys = useMemo(() => {
    const matchKey = menuItems.find((item) =>
      location.pathname.startsWith(`${item?.key}`)
    )?.key;
    if (matchKey) {
      return [`${matchKey}`];
    } else {
      return [];
    }
  }, [location.pathname]);
  const navigateTo = (key: string) => {
    navigate(key);
  };
  return (
    <Container
      css={css`
        background: ${theme.colorBgContainer};
        border-bottom: 1px solid ${theme.colorBorder};
      `}
    >
      <Menu
        selectedKeys={selectedKeys}
        onClick={({ key }) => navigateTo(key)}
        style={{ borderBottom: "none" }}
        mode="horizontal"
        items={menuItems}
      />
    </Container>
  );
};
