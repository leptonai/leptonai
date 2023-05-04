import { FC, useEffect } from "react";
import styled from "@emotion/styled";
import { Card, Col, Row, Statistic } from "antd";
import { useInject } from "@lepton-libs/di";
import { ModelService } from "@lepton-dashboard/services/model.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { TitleService } from "@lepton-dashboard/services/title.service.ts";

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
  const models = useStateFromObservable(() => modelService.list(), []);
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  return (
    <Container>
      <Row gutter={[16, 32]}>
        <Col span={5}>
          <Card bordered={false}>
            <Statistic title="Total Models" value={models.length} />
          </Card>
        </Col>
        <Col span={5}>
          <Card bordered={false}>
            <Statistic title="Total Deployments" value={deployments.length} />
          </Card>
        </Col>
      </Row>
    </Container>
  );
};
