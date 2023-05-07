import { FC, useMemo } from "react";
import { useParams } from "react-router-dom";
import { useInject } from "@lepton-libs/di";
import { ModelService } from "@lepton-dashboard/services/model.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import {
  Breadcrumb,
  Col,
  List as AntdList,
  Row,
  Timeline,
  Typography,
} from "antd";
import { Link } from "@lepton-dashboard/components/link";
import { ExperimentOutlined } from "@ant-design/icons";
import { BreadcrumbHeader } from "@lepton-dashboard/routers/models/components/breadcrumb-header";
import { Card } from "@lepton-dashboard/components/card";
import { ModelCard } from "@lepton-dashboard/components/model-card";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import dayjs from "dayjs";
import { DeploymentCard } from "@lepton-dashboard/components/deployment-card";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";

export const Versions: FC = () => {
  const { name } = useParams();
  const modelService = useInject(ModelService);
  const groupedModel = useStateFromObservable(
    () => modelService.groupId(name!),
    undefined
  );
  const theme = useAntdTheme();
  const deploymentService = useInject(DeploymentService);
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  const filteredDeployments = useMemo(() => {
    const ids =
      groupedModel?.data.filter((m) => m.name === name).map((i) => i.id) || [];
    return deployments.filter((d) => ids.indexOf(d.photon_id) !== -1);
  }, [deployments, name, groupedModel]);
  const models = groupedModel?.data || [];

  return (
    <Row gutter={[0, 24]}>
      <Col span={24}>
        <BreadcrumbHeader>
          <Breadcrumb
            items={[
              {
                title: (
                  <>
                    <ExperimentOutlined />
                    <Link to="../../models">
                      <span>Models</span>
                    </Link>
                  </>
                ),
              },
              {
                title: name,
              },
            ]}
          />
        </BreadcrumbHeader>
      </Col>
      <Col span={24}>
        <Card title="Version History">
          <Timeline
            css={css`
              padding: 8px 0;
            `}
            items={models.map((m) => {
              return {
                key: m.id,
                color: theme.colorTextSecondary,
                dot: <ExperimentOutlined />,
                children: (
                  <Col key={m.id} span={24}>
                    <Typography.Paragraph
                      style={{ paddingTop: "1px" }}
                      type="secondary"
                    >
                      Create at {dayjs(m.created_at).format("lll")}
                    </Typography.Paragraph>
                    <ModelCard action={true} shadowless={true} model={m} />
                  </Col>
                ),
              };
            })}
          />
        </Card>
      </Col>
      <Col span={24}>
        <Card title="Deployments" paddingless>
          <AntdList
            itemLayout="horizontal"
            dataSource={filteredDeployments}
            renderItem={(deployment) => (
              <AntdList.Item style={{ padding: 0, display: "block" }}>
                <DeploymentCard modelPage deployment={deployment} borderless />
              </AntdList.Item>
            )}
          />
        </Card>
      </Col>
    </Row>
  );
};
