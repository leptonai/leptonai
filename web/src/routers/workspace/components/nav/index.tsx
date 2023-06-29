import { Badge, TabsProps } from "antd";
import { FC } from "react";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import {
  CarbonIcon,
  DeploymentIcon,
  PhotonIcon,
} from "@lepton-dashboard/components/icons";
import { IndicatorService } from "@lepton-dashboard/routers/workspace/services/indicator.service";
import { Asterisk, DataVolume, Settings, Workspace } from "@carbon/icons-react";
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
    {
      label: (
        <span id="nav-storage">
          <CarbonIcon icon={<DataVolume />} />
          Storage
        </span>
      ),
      key: `${pathname}/storage`,
    },
    {
      key: `${pathname}/secrets`,
      label: (
        <span id="nav-secrets">
          <CarbonIcon icon={<Asterisk />} />
          Secrets
        </span>
      ),
    },
    {
      label: (
        <span id="nav-settings">
          <CarbonIcon icon={<Settings />} /> Settings
        </span>
      ),
      key: `${pathname}/settings`,
    },
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
