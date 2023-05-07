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
import {
  CloseOutlined,
  DeleteOutlined,
  EditOutlined,
  ExperimentOutlined,
  EyeOutlined,
} from "@ant-design/icons";
import { Status } from "@lepton-dashboard/routers/deployments/components/status";
import { KeyValue } from "@lepton-dashboard/components/key-value";
import { useInject } from "@lepton-libs/di";
import { ModelService } from "@lepton-dashboard/services/model.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { ModelCard } from "@lepton-dashboard/components/model-card";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { RefreshService } from "@lepton-dashboard/services/refresh.service.ts";

export const DeploymentCard: FC<{
  deployment: Deployment;
  borderless?: boolean;
  shadowless?: boolean;
  modelPage?: boolean;
}> = ({
  deployment,
  borderless = false,
  shadowless = false,
  modelPage = false,
}) => {
  const modelService = useInject(ModelService);
  const refreshService = useInject(RefreshService);
  const deploymentService = useInject(DeploymentService);
  const model = useStateFromObservable(
    () => modelService.id(deployment.photon_id),
    undefined
  );
  const { message } = App.useApp();
  return (
    <Card borderless={borderless} shadowless={shadowless}>
      <Row gutter={16} wrap={true}>
        <Col flex="600px">
          <KeyValue
            value={
              <Link
                to={`/deployments/detail/${deployment.id}/mode/view`}
                relative="route"
              >
                <span
                  css={css`
                    font-size: 16px;
                    font-weight: 500;
                  `}
                >
                  {deployment.name}
                </span>
              </Link>
            }
          />
          <KeyValue
            value={
              <Typography.Text type="secondary">
                {deployment.id}
              </Typography.Text>
            }
          />
          <Space size={4} split={<Divider type="vertical" />}>
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
            size={4}
            style={{ display: "flex" }}
            split={<Divider type="vertical" />}
          >
            <KeyValue value={<Status status={deployment.status.state} />} />
            <KeyValue
              title="Min Replicas"
              value={deployment.resource_requirement.min_replicas}
            />
          </Space>
          <Space size={4} split={<Divider type="vertical" />}>
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
          <Space size={4} split={<Divider type="vertical" />}>
            {!modelPage && (
              <KeyValue
                value={
                  <Popover
                    content={
                      <ModelCard
                        detail
                        id={false}
                        action={false}
                        model={model}
                        borderless
                        shadowless
                      />
                    }
                  >
                    <span>
                      <Link
                        icon={<ExperimentOutlined />}
                        to={`/models/detail/${model?.id}`}
                        relative="route"
                      >
                        Model
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
                <Link
                  icon={<EditOutlined />}
                  to={`/deployments/detail/${deployment.id}/mode/edit`}
                  relative="route"
                >
                  Edit
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
