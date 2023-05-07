import { Badge, Tabs, TabsProps } from "antd";
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
  padding: 0 24px;
  z-index: 2;
  flex: 0 0 46px;
  top: 0;
  .ant-tabs-nav::before {
    display: none;
  }
`;
const StyledBadge = styled(Badge)`
  margin-left: 12px;
  top: -1px;
`;

export const Nav: FC = () => {
  const modelService = useInject(ModelService);
  const deploymentService = useInject(DeploymentService);
  const models = useStateFromObservable(() => modelService.groups(), []);
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  const menuItems: TabsProps["items"] = useMemo(
    () => [
      {
        label: (
          <>
            <AppstoreOutlined />
            Dashboard
          </>
        ),
        key: "/dashboard",
      },
      {
        label: (
          <>
            <ExperimentOutlined />
            Models
            <StyledBadge size="small" color="#ccc" count={models.length} />
          </>
        ),
        key: "/models",
      },
      {
        label: (
          <>
            <RocketOutlined />
            Deployments
            <StyledBadge size="small" color="#ccc" count={deployments.length} />
          </>
        ),
        key: "/deployments",
      },
    ],
    [deployments, models]
  );
  const theme = useAntdTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const selectedKey = useMemo(() => {
    return menuItems.find((item) =>
      location.pathname.startsWith(`${item?.key}`)
    )?.key;
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
      <Tabs
        moreIcon={null}
        tabBarGutter={32}
        tabBarStyle={{ marginBottom: 0 }}
        activeKey={selectedKey}
        items={menuItems}
        onTabClick={(key) => navigateTo(key)}
      />
    </Container>
  );
};
