import { Badge, Tabs, TabsProps } from "antd";
import styled from "@emotion/styled";
import { FC, useMemo } from "react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";
import { useLocation, useNavigate } from "react-router-dom";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service.ts";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import {
  CarbonIcon,
  DeploymentIcon,
  PhotonIcon,
} from "@lepton-dashboard/components/icons";
import { NotificationService } from "@lepton-dashboard/services/notification.service.ts";
import { Workspace } from "@carbon/icons-react";

const Container = styled.div`
  position: sticky;
  padding: 0 24px;
  z-index: 2;
  flex: 0 0 46px;
  top: 0;
  .ant-tabs-nav::before {
    display: none;
  }
  .ant-tabs-nav-operations {
    display: none !important;
  }
`;

const StyledBadge = styled(Badge)`
  margin-left: 12px;
  top: -1px;
  min-width: 20px;
`;

const PhotonLabel: FC = () => {
  const theme = useAntdTheme();
  const photonService = useInject(PhotonService);
  const notificationService = useInject(NotificationService);
  const notify = useStateFromObservable(
    () => notificationService.photonNotify$,
    false
  );
  const photons = useStateFromObservable(() => photonService.listGroups(), []);
  return (
    <>
      <PhotonIcon />
      Photons
      <StyledBadge
        showZero
        size="small"
        color={notify ? theme.colorLink : theme.colorTextTertiary}
        count={photons.length}
      />
    </>
  );
};

const DeploymentLabel: FC = () => {
  const theme = useAntdTheme();
  const notificationService = useInject(NotificationService);
  const notify = useStateFromObservable(
    () => notificationService.deploymentNotify$,
    false
  );
  const deploymentService = useInject(DeploymentService);
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  return (
    <>
      <DeploymentIcon />
      Deployments
      <StyledBadge
        showZero
        size="small"
        color={notify ? theme.colorLink : theme.colorTextTertiary}
        count={deployments.length}
      />
    </>
  );
};
const menuItems: TabsProps["items"] = [
  {
    label: (
      <>
        <CarbonIcon icon={<Workspace />} />
        Dashboard
      </>
    ),
    key: "/dashboard",
  },
  {
    label: <PhotonLabel />,
    key: "/photons",
  },
  {
    label: <DeploymentLabel />,
    key: "/deployments",
  },
];

export const Nav: FC = () => {
  const theme = useAntdTheme();
  const notificationService = useInject(NotificationService);
  const location = useLocation();
  const navigate = useNavigate();
  const selectedKey = useMemo(() => {
    return menuItems.find((item) =>
      location.pathname.startsWith(`${item?.key}`)
    )?.key;
  }, [location.pathname]);
  const navigateTo = useMemo(
    () => (key: string) => {
      if (key === "/deployments") {
        notificationService.updateDeploymentNotify();
      } else if (key === "/photons") {
        notificationService.updatePhotonNotify();
      }
      navigate(key);
    },
    [navigate, notificationService]
  );
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
