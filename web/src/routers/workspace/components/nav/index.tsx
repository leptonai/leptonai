import { Badge } from "antd";
import { FC } from "react";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import {
  CarbonIcon,
  DeploymentIcon,
  PhotonIcon,
} from "@lepton-dashboard/components/icons";
import { IndicatorService } from "@lepton-dashboard/routers/workspace/services/indicator.service";
import { Folder, Settings, Workspace } from "@carbon/icons-react";
import { TabsNav } from "../../../../components/tabs-nav";
import { useResolvedPath } from "react-router-dom";

const PhotonLabel: FC = () => {
  const notificationService = useInject(IndicatorService);
  const notify = useStateFromObservable(
    () => notificationService.photonNotify$,
    false
  );
  return (
    <Badge dot={notify} offset={[6, 0]}>
      <PhotonIcon />
      Photons
    </Badge>
  );
};

const DeploymentLabel: FC = () => {
  const notificationService = useInject(IndicatorService);
  const notify = useStateFromObservable(
    () => notificationService.deploymentNotify$,
    false
  );
  return (
    <Badge dot={notify} offset={[6, 0]}>
      <DeploymentIcon />
      Deployments
    </Badge>
  );
};

export const Nav: FC = () => {
  const { pathname } = useResolvedPath("");

  const menuItems = [
    {
      label: (
        <span id="nav-dashboard">
          <CarbonIcon icon={<Workspace />} />
          Dashboard
        </span>
      ),
      prefix: `${pathname}/dashboard`,
      key: `${pathname}/dashboard`,
    },
    {
      label: (
        <span id="nav-photons">
          <PhotonLabel />
        </span>
      ),
      prefix: `${pathname}/photons`,
      key: `${pathname}/photons/list`,
    },
    {
      label: (
        <span id="nav-deployments">
          <DeploymentLabel />
        </span>
      ),
      prefix: `${pathname}/deployments`,
      key: `${pathname}/deployments/list`,
    },

    {
      label: (
        <span id="nav-storage">
          <CarbonIcon icon={<Folder />} />
          Storage
        </span>
      ),
      key: `${pathname}/storage`,
    },

    {
      label: (
        <span id="nav-settings">
          <CarbonIcon icon={<Settings />} /> Settings
        </span>
      ),
      prefix: `${pathname}/settings`,
      key: `${pathname}/settings/general`,
    },
  ];

  const notificationService = useInject(IndicatorService);
  const keyActive = (key: string) => {
    if (key === `${pathname}/deployments/list`) {
      notificationService.updateDeploymentNotify();
    } else if (key === `${pathname}/photons/list`) {
      notificationService.updatePhotonNotify();
    }
  };
  return <TabsNav menuItems={menuItems} keyActive={keyActive} />;
};
