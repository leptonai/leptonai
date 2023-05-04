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
import { useInject } from "@lepton-libs/di";
import { ModelService } from "@lepton-dashboard/services/model.service.ts";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";

const Container = styled.div`
  position: sticky;
  padding: 0 8px;
  z-index: 1;
  flex: 0 0 45px;
  top: 0;
`;
const StyledBadge = styled(Badge)`
  margin-left: 12px;
  top: -1px;
`;

export const Nav: FC = () => {
  const modelService = useInject(ModelService);
  const deploymentService = useInject(DeploymentService);
  const models = useStateFromObservable(() => modelService.listGroup(), []);
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  const menuItems: MenuProps["items"] = useMemo(
    () => [
      {
        label: <>Dashboard</>,
        key: "/dashboard",
        icon: <AppstoreOutlined />,
      },
      {
        label: (
          <>
            Models
            <StyledBadge size="small" color="#ccc" count={models.length} />
          </>
        ),
        key: "/models",
        icon: <ExperimentOutlined />,
      },
      {
        label: (
          <>
            Deployments
            <StyledBadge size="small" color="#ccc" count={deployments.length} />
          </>
        ),
        key: "/deployments",
        icon: <RocketOutlined />,
      },
    ],
    [deployments, models]
  );
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
  }, [location.pathname, menuItems]);
  const navigateTo = (key: string) => {
    navigate(key);
  };
  return (
    <Container
      css={css`
        background: ${theme.colorBgContainer};
        border-bottom: 1px solid ${theme.colorBorder};
        box-shadow: ${theme.boxShadowTertiary};
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
