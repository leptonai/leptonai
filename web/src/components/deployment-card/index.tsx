import { FC } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment.ts";
import { Card } from "@lepton-dashboard/components/card";
import {
  App,
  Button,
  Col,
  Divider,
  Popconfirm,
  Popover,
  Row,
  Space,
  Tooltip,
  Typography,
} from "antd";
import dayjs from "dayjs";
import { Link } from "@lepton-dashboard/components/link";
import { css } from "@emotion/react";
import { Hoverable } from "@lepton-dashboard/components/hoverable";
import { CloseOutlined, DeleteOutlined, EyeOutlined } from "@ant-design/icons";
import { KeyValue } from "@lepton-dashboard/components/key-value";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { RefreshService } from "@lepton-dashboard/services/refresh.service.ts";
import { DeploymentIcon, PhotonIcon } from "@lepton-dashboard/components/icons";
import { DeploymentStatus } from "@lepton-dashboard/components/refactor/deployment-status";
import { PhotonItem } from "@lepton-dashboard/components/refactor/photon-item";

export const DeploymentCard: FC<{
  deployment: Deployment;
  borderless?: boolean;
  shadowless?: boolean;
  photonPage?: boolean;
}> = ({
  deployment,
  borderless = false,
  shadowless = false,
  photonPage = false,
}) => {
  const photonService = useInject(PhotonService);
  const refreshService = useInject(RefreshService);
  const deploymentService = useInject(DeploymentService);
  const photon = useStateFromObservable(
    () => photonService.id(deployment.photon_id),
    undefined
  );
  const { message } = App.useApp();
  return (
    <Card borderless={borderless} shadowless={shadowless}>
      <Row gutter={16} wrap={true}>
        <Col flex="600px">
          <KeyValue
            value={
              <span
                css={css`
                  font-size: 16px;
                  font-weight: 500;
                `}
              >
                <Link
                  icon={<DeploymentIcon />}
                  to={`/deployments/detail/${deployment.id}/mode/view`}
                  relative="route"
                >
                  {deployment.name}
                </Link>
              </span>
            }
          />
          <KeyValue
            value={
              <Typography.Text type="secondary">
                {deployment.id}
              </Typography.Text>
            }
          />
          <Space split={<Divider type="vertical" />}>
            <KeyValue
              title="MEM"
              value={`${deployment.resource_requirement.memory} MB`}
            />
            <KeyValue title="CPU" value={deployment.resource_requirement.cpu} />
          </Space>
          <KeyValue
            title="Accelerator"
            value={
              deployment.resource_requirement.accelerator_type ? (
                <>
                  {deployment.resource_requirement.accelerator_type}
                  <CloseOutlined
                    css={css`
                      margin: 0 4px;
                    `}
                  />
                  {deployment.resource_requirement.accelerator_num}
                </>
              ) : (
                "No Accelerator"
              )
            }
          />
        </Col>
        <Col flex="auto">
          <Space
            style={{ display: "flex" }}
            split={<Divider type="vertical" />}
          >
            <KeyValue
              value={<DeploymentStatus status={deployment.status.state} />}
            />
            <KeyValue
              title="Min Replicas"
              value={deployment.resource_requirement.min_replicas}
            />
          </Space>
          <Space split={<Divider type="vertical" />}>
            <Tooltip title={deployment.status.endpoint.external_endpoint}>
              <span>
                <KeyValue value={<Hoverable>External Endpoint</Hoverable>} />
              </span>
            </Tooltip>
            <Tooltip title={deployment.status.endpoint.internal_endpoint}>
              <span>
                <KeyValue value={<Hoverable>Internal Endpoint</Hoverable>} />
              </span>
            </Tooltip>
          </Space>
          <KeyValue
            title="Create Time"
            value={dayjs(deployment.created_at).format("lll")}
          />
          <Space split={<Divider type="vertical" />}>
            {!photonPage && (
              <KeyValue
                value={
                  <Popover content={<PhotonItem showDetail photon={photon} />}>
                    <span>
                      <Link
                        icon={<PhotonIcon />}
                        to={`/photons/detail/${photon?.id}`}
                        relative="route"
                      >
                        Photon
                      </Link>
                    </span>
                  </Popover>
                }
              />
            )}
            <KeyValue
              value={
                <Link
                  icon={<EyeOutlined />}
                  to={`/deployments/detail/${deployment.id}/mode/view`}
                  relative="route"
                >
                  Detail
                </Link>
              }
            />
            <KeyValue
              value={
                <Popconfirm
                  title="Delete the deployment"
                  description="Are you sure to delete?"
                  onConfirm={() => {
                    void message.loading({
                      content: `Deleting deployment ${deployment.name}, please wait...`,
                      key: "delete-deployment",
                      duration: 0,
                    });
                    deploymentService.delete(deployment.id).subscribe({
                      next: () => {
                        message.destroy("delete-deployment");
                        void message.success(
                          `Successfully deleted deployment ${deployment.name}`
                        );
                        refreshService.refresh();
                      },
                      error: () => {
                        message.destroy("delete-deployment");
                      },
                    });
                  }}
                >
                  <Button
                    style={{ padding: 0 }}
                    danger
                    size="small"
                    type="link"
                    icon={<DeleteOutlined />}
                  >
                    Delete
                  </Button>
                </Popconfirm>
              }
            />
          </Space>
        </Col>
      </Row>
    </Card>
  );
};
