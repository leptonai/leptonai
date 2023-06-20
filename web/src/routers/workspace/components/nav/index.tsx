import { Badge, TabsProps } from "antd";
import styled from "@emotion/styled";
import { FC } from "react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import {
  CarbonIcon,
  DeploymentIcon,
  PhotonIcon,
} from "@lepton-dashboard/components/icons";
import { IndicatorService } from "@lepton-dashboard/routers/workspace/services/indicator.service";
import { Workspace } from "@carbon/icons-react";
import { TabsNav } from "../../../../components/tabs-nav";
import { useResolvedPath } from "react-router-dom";

const StyledBadge = styled(Badge)`
  margin-left: 12px;
  top: -1px;
  min-width: 20px;
`;

const PhotonLabel: FC = () => {
  const theme = useAntdTheme();
  const photonService = useInject(PhotonService);
  const notificationService = useInject(IndicatorService);
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
  const notificationService = useInject(IndicatorService);
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

export const Nav: FC = () => {
  const { pathname } = useResolvedPath("");
  const menuItems: TabsProps["items"] = [
    {
      label: (
        <span id="nav-dashboard">
          <CarbonIcon icon={<Workspace />} />
          Dashboard
        </span>
      ),
      key: `${pathname}/dashboard`,
    },
    {
      label: (
        <span id="nav-photons">
          <PhotonLabel />
        </span>
      ),
      key: `${pathname}/photons`,
    },
    {
      label: (
        <span id="nav-deployments">
          <DeploymentLabel />
        </span>
      ),
      key: `${pathname}/deployments`,
    },
    // {
    //   label: (
    //     <span id="nav-settings">
    //       <CarbonIcon icon={<Settings />} /> Settings
    //     </span>
    //   ),
    //   key: `${pathname}/settings`,
    // },
  ];

  const notificationService = useInject(IndicatorService);
  const keyActive = (key: string) => {
    if (key === `${pathname}/deployments`) {
      notificationService.updateDeploymentNotify();
    } else if (key === `${pathname}/photons`) {
      notificationService.updatePhotonNotify();
    }
  };
  return <TabsNav menuItems={menuItems} keyActive={keyActive} />;
};
