import { Badge, TabsProps } from "antd";
import styled from "@emotion/styled";
import { FC } from "react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { css } from "@emotion/react";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import {
  CarbonIcon,
  DeploymentIcon,
  PhotonIcon,
} from "@lepton-dashboard/components/icons";
import { NotificationService } from "@lepton-dashboard/services/notification.service";
import { Workspace } from "@carbon/icons-react";
import { TabsNav } from "@lepton-dashboard/components/tabs-nav";

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
  const keyActive = (key: string) => {
    if (key === "/deployments") {
      notificationService.updateDeploymentNotify();
    } else if (key === "/photons") {
      notificationService.updatePhotonNotify();
    }
  };
  return (
    <Container
      css={css`
        background: ${theme.colorBgContainer};
        border-bottom: 1px solid ${theme.colorBorder};
        box-shadow: ${theme.boxShadowTertiary};
      `}
    >
      <TabsNav menuItems={menuItems} keyActive={keyActive} />
    </Container>
  );
};
