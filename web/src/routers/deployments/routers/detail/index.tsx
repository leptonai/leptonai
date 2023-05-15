import { FC, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import {
  App,
  Button,
  Col,
  Descriptions,
  InputNumber,
  Popover,
  Row,
  Space,
  Typography,
} from "antd";
import { BreadcrumbHeader } from "@lepton-dashboard/routers/photons/components/breadcrumb-header";
import { Link } from "@lepton-dashboard/components/link";
import { EditOutlined } from "@ant-design/icons";
import { Card } from "@lepton-dashboard/components/card";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { Request } from "@lepton-dashboard/routers/deployments/components/request";
import { DeploymentIcon } from "@lepton-dashboard/components/icons";
import { DeploymentStatus } from "../../../../components/deployment-status";
import { DateParser } from "@lepton-dashboard/components/date-parser";
import { PhotonService } from "@lepton-dashboard/services/photon.service.ts";
import { mergeMap, of } from "rxjs";
import { PhotonItem } from "@lepton-dashboard/components/photon-item";

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
  const photonService = useInject(PhotonService);
  const photon = useStateFromObservable(
    () =>
      deploymentService
        .id(id!)
        .pipe(
          mergeMap((deployment) =>
            deployment ? photonService.id(deployment.photon_id) : of(undefined)
          )
        ),
    undefined
  );

  return deployment ? (
    <Row gutter={[0, 24]}>
      <Col span={24}>
        <BreadcrumbHeader
          items={[
            {
              title: (
                <>
                  <DeploymentIcon />
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
          <Descriptions bordered size="small" column={{ xs: 1, sm: 1, md: 2 }}>
            <Descriptions.Item label="Name">
              {deployment.name}
            </Descriptions.Item>
            <Descriptions.Item label="ID">{deployment.id}</Descriptions.Item>
            <Descriptions.Item label="Status">
              <DeploymentStatus status={deployment.status.state} />
            </Descriptions.Item>
            <Descriptions.Item label="Photon">
              {photon?.name ? (
                <Popover
                  placement="bottomLeft"
                  content={<PhotonItem photon={photon} />}
                >
                  <span>
                    <Link to={`/photons/versions/${photon?.name}`}>
                      {photon?.name}
                    </Link>
                  </span>
                </Popover>
              ) : (
                "-"
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Created At">
              <DateParser date={deployment.created_at} detail />
            </Descriptions.Item>
            <Descriptions.Item label="External Endpoint">
              <Typography.Text copyable>
                {deployment.status.endpoint.external_endpoint || "-"}
              </Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="CPU">
              {deployment.resource_requirement.cpu}
            </Descriptions.Item>
            <Descriptions.Item label="Internal Endpoint">
              <Typography.Text copyable>
                {deployment.status.endpoint.internal_endpoint || "-"}
              </Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="Memory">
              {deployment.resource_requirement.memory} MB
            </Descriptions.Item>
            <Descriptions.Item label="Accelerator">
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
        <Request url={deployment.status.endpoint.external_endpoint} />
      </Col>
    </Row>
  ) : null;
};
