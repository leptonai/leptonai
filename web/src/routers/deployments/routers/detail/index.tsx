import { FC, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import {
  App,
  Breadcrumb,
  Button,
  Col,
  Descriptions,
  InputNumber,
  Row,
  Space,
} from "antd";
import { BreadcrumbHeader } from "@lepton-dashboard/routers/models/components/breadcrumb-header";
import { Link } from "@lepton-dashboard/components/link";
import { EditOutlined, RocketOutlined } from "@ant-design/icons";
import { Card } from "@lepton-dashboard/components/card";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import dayjs from "dayjs";
import { Status } from "@lepton-dashboard/routers/deployments/components/status";
import { ModelService } from "@lepton-dashboard/services/model.service.ts";
import { ModelCard } from "@lepton-dashboard/components/model-card";
import { mergeMap } from "rxjs";

export const Detail: FC = () => {
  const { id, mode } = useParams();
  const { message } = App.useApp();
  const navigate = useNavigate();
  const editMode = mode === "edit";
  const deploymentService = useInject(DeploymentService);
  const [minReplicas, setMinReplicas] = useState<number | null>(null);
  const deployment = useStateFromObservable(
    () => deploymentService.id(id!),
    undefined,
    {
      next: (value) =>
        setMinReplicas(value?.resource_requirement?.min_replicas ?? null),
    }
  );
  const modelService = useInject(ModelService);
  const model = useStateFromObservable(
    () =>
      deploymentService
        .id(id!)
        .pipe(mergeMap((d) => modelService.id(d!.photon_id))),
    undefined
  );

  return deployment ? (
    <Row gutter={[0, 24]}>
      <Col span={24}>
        <BreadcrumbHeader>
          <Breadcrumb
            items={[
              {
                title: (
                  <>
                    <RocketOutlined />
                    <Link to="../../deployments">
                      <span>Deployments</span>
                    </Link>
                  </>
                ),
              },
              {
                title: deployment.name,
              },
            ]}
          />
        </BreadcrumbHeader>
      </Col>

      <Col span={24}>
        <Card
          title="Deployment Detail"
          extra={
            !editMode && (
              <Button
                type="primary"
                size="small"
                icon={<EditOutlined />}
                onClick={() => navigate("../edit", { relative: "path" })}
              >
                Edit
              </Button>
            )
          }
        >
          <Descriptions bordered size="small" column={{ xs: 1, sm: 2 }}>
            <Descriptions.Item label="Name">
              {deployment.name}
            </Descriptions.Item>
            <Descriptions.Item label="ID">{deployment.id}</Descriptions.Item>
            <Descriptions.Item label="Create Time">
              {dayjs(deployment.created_at).format("lll")}
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <Status status={deployment.status.state} />
            </Descriptions.Item>
            <Descriptions.Item label="Internal Endpoint">
              {deployment.status.endpoint.internal_endpoint || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="External Endpoint">
              {deployment.status.endpoint.external_endpoint || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Memory">
              {deployment.resource_requirement.memory} MB
            </Descriptions.Item>
            <Descriptions.Item label="CPU">
              {deployment.resource_requirement.cpu}
            </Descriptions.Item>
            <Descriptions.Item label="Accelerator Type">
              {deployment.resource_requirement.accelerator_type || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Accelerator Number">
              {deployment.resource_requirement.accelerator_num || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="Min Replicas">
              {editMode ? (
                <InputNumber
                  value={minReplicas}
                  min={0}
                  onChange={(e) => setMinReplicas(e)}
                />
              ) : (
                deployment.resource_requirement.min_replicas
              )}
            </Descriptions.Item>
          </Descriptions>
          {editMode && (
            <Space style={{ marginTop: "24px" }}>
              <Button
                type="primary"
                onClick={() => {
                  if (minReplicas !== null && minReplicas !== undefined) {
                    void message.loading({
                      content: "Update deployment, please wait...",
                      duration: 0,
                      key: "update-deployment",
                    });
                    deploymentService
                      .update(deployment.id, minReplicas)
                      .subscribe({
                        next: () => {
                          message.destroy("update-deployment");
                          navigate("../view", { relative: "path" });
                        },
                        error: () => {
                          message.destroy("update-deployment");
                        },
                      });
                  }
                }}
              >
                Save
              </Button>
              <Button onClick={() => navigate("../view", { relative: "path" })}>
                Cancel
              </Button>
            </Space>
          )}
        </Card>
      </Col>
      <Col span={24}>
        <Card title="Model Detail">
          <ModelCard
            inModel={true}
            borderless
            shadowless
            paddingless
            model={model}
          />
        </Card>
      </Col>
    </Row>
  ) : null;
};
