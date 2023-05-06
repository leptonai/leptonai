import { FC, useEffect } from "react";
import styled from "@emotion/styled";
import { Col, Row, Statistic } from "antd";
import { useInject } from "@lepton-libs/di";
import { ModelService } from "@lepton-dashboard/services/model.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { TitleService } from "@lepton-dashboard/services/title.service.ts";
import { Card } from "@lepton-dashboard/components/card";

const Container = styled.div`
  flex: 1 1 auto;
`;

export const Dashboard: FC = () => {
  const modelService = useInject(ModelService);
  const titleService = useInject(TitleService);
  useEffect(() => {
    titleService.setTitle("Dashboard");
  }, [titleService]);
  const deploymentService = useInject(DeploymentService);
  const groupedModels = useStateFromObservable(
    () => modelService.listGroup(),
    []
  );
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  return (
    <Container>
      <Row gutter={[16, 32]}>
        <Col flex="200px">
          <Card direction="horizontal">
            <Statistic title="Total Models" value={groupedModels.length} />
          </Card>
        </Col>
        <Col flex="200px">
          <Card direction="horizontal">
            <Statistic title="Total Deployments" value={deployments.length} />
          </Card>
        </Col>
      </Row>
    </Container>
  );
};
