import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { GettingStarted } from "../../../../components/getting-started";
import { Timeline } from "@lepton-dashboard/routers/workspace/routers/detail/routers/dashboard/components/timeline";
import { FC } from "react";
import styled from "@emotion/styled";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { useStateFromBehaviorSubject } from "@lepton-libs/hooks/use-state-from-observable";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";

const Container = styled.div`
  flex: 1 1 auto;
`;

export const Dashboard: FC = () => {
  const photonService = useInject(PhotonService);
  useDocumentTitle("Dashboard");
  const deploymentService = useInject(DeploymentService);
  const photonGroups = useStateFromBehaviorSubject(photonService.listGroups());
  const deployments = useStateFromBehaviorSubject(deploymentService.list());
  if (photonGroups.length === 0 && deployments.length === 0) {
    return <GettingStarted />;
  } else {
    return (
      <Container>
        <Timeline deployments={deployments} photonGroups={photonGroups} />
        <GettingStarted />
      </Container>
    );
  }
};
