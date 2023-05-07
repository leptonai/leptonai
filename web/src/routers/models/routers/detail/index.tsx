import { FC, useMemo } from "react";
import { useParams } from "react-router-dom";
import { useInject } from "@lepton-libs/di";
import { ModelService } from "@lepton-dashboard/services/model.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { Breadcrumb, Col, List as AntdList, Row } from "antd";
import { BreadcrumbHeader } from "@lepton-dashboard/routers/models/components/breadcrumb-header";
import { Link } from "@lepton-dashboard/components/link";
import { ExperimentOutlined } from "@ant-design/icons";
import { ModelCard } from "@lepton-dashboard/components/model-card";
import { Card } from "@lepton-dashboard/components/card";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { DeploymentCard } from "@lepton-dashboard/components/deployment-card";

export const Detail: FC = () => {
  const { id } = useParams();
  const modelService = useInject(ModelService);
  const model = useStateFromObservable(() => modelService.id(id!), undefined);
  const deploymentService = useInject(DeploymentService);
  const deployments = useStateFromObservable(
    () => deploymentService.list(),
    []
  );
  const filteredDeployments = useMemo(() => {
    return deployments.filter((d) => d.photon_id === id);
  }, [deployments, id]);

  return model ? (
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
                title: (
                  <Link to={`../../versions/${model.name}`}>{model.name}</Link>
                ),
              },
              {
                title: model.id,
              },
            ]}
          />
        </BreadcrumbHeader>
      </Col>
      <Col span={24}>
        <Card title="Model Detail">
          <ModelCard
            paddingless
            borderless
            shadowless
            model={model}
            detail={true}
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
  ) : null;
};
