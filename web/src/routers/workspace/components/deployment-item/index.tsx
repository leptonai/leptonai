import { FC } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import {
  App,
  Button,
  Col,
  Divider,
  Popconfirm,
  Popover,
  Row,
  Space,
  Typography,
} from "antd";
import { Link } from "@lepton-dashboard/routers/workspace/components/link";
import { css } from "@emotion/react";
import { Description } from "@lepton-dashboard/routers/workspace/components/description";
import { CarbonIcon, PhotonIcon } from "@lepton-dashboard/components/icons";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import {
  Api_1,
  Chip,
  CopyFile,
  FlowModeler,
  MessageQueue,
  Replicate,
  Time,
} from "@carbon/icons-react";
import { CloseOutlined, DeleteOutlined } from "@ant-design/icons";
import { DeploymentStatus } from "@lepton-dashboard/routers/workspace/components/deployment-status";
import { DateParser } from "@lepton-dashboard/routers/workspace/components/date-parser";
import { useInject } from "@lepton-libs/di";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { PhotonItem } from "@lepton-dashboard/routers/workspace/components/photon-item";
import { Hoverable } from "@lepton-dashboard/routers/workspace/components/hoverable";
import { EditDeployment } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/edit-deployment";
import { useNavigate } from "react-router-dom";
import { Envs } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/envs";
import { VersionIndicator } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/version-indicator";
import { WorkspaceTrackerService } from "../../services/workspace-tracker.service";

export const DeploymentItem: FC<{ deployment: Deployment }> = ({
  deployment,
}) => {
  const theme = useAntdTheme();
  const { message } = App.useApp();
  const navigate = useNavigate();
  const refreshService = useInject(RefreshService);
  const deploymentService = useInject(DeploymentService);
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const photonService = useInject(PhotonService);
  const photon = useStateFromObservable(
    () => photonService.id(deployment.photon_id),
    undefined
  );
  return (
    <Row gutter={[16, 8]}>
      <Col span={24}>
        <Row
          gutter={16}
          css={css`
            height: 28px;
            overflow: hidden;
          `}
        >
          <Col flex="1 1 auto">
            <Link
              css={css`
                color: ${theme.colorTextHeading};
              `}
              icon={<DeploymentStatus status={deployment.status.state} />}
              to={`/workspace/${workspaceTrackerService.name}/deployments/detail/${deployment.id}`}
              relative="route"
            >
              <Description.Item
                css={css`
                  font-weight: 600;
                  font-size: 16px;
                `}
                term={deployment.name}
              />
            </Link>
          </Col>
          <Col flex="0 0 auto">
            <Space size={0} split={<Divider type="vertical" />}>
              <EditDeployment deployment={deployment} />
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
                      navigate(
                        `/workspace/${workspaceTrackerService.name}/deployments/list`,
                        { relative: "route" }
                      );
                    },
                    error: () => {
                      message.destroy("delete-deployment");
                    },
                  });
                }}
              >
                <Button
                  type="text"
                  danger
                  size="small"
                  icon={<DeleteOutlined />}
                >
                  Delete
                </Button>
              </Popconfirm>
            </Space>
          </Col>
        </Row>
      </Col>
      <Col span={24}>
        <Row gutter={[0, 4]}>
          <Col flex="0 0 400px">
            <Row gutter={[0, 4]}>
              <Col span={24}>
                <Description.Item
                  icon={<PhotonIcon />}
                  description={
                    photon?.name ? (
                      <Space>
                        <Popover
                          placement="bottomLeft"
                          content={
                            <div
                              css={css`
                                width: min-content;
                              `}
                            >
                              <PhotonItem photon={photon} />
                            </div>
                          }
                        >
                          <span>
                            <Link
                              to={`/workspace/${workspaceTrackerService.name}/photons/detail/${photon?.id}`}
                            >
                              {photon?.name}
                              <VersionIndicator
                                photonId={deployment.photon_id}
                              />
                            </Link>
                          </span>
                        </Popover>
                      </Space>
                    ) : (
                      "-"
                    )
                  }
                />
              </Col>
              <Col span={24}>
                <Description.Item
                  icon={<CarbonIcon icon={<Time />} />}
                  description={
                    <DateParser detail date={deployment.created_at} />
                  }
                />
              </Col>
              <Col span={24}>
                <Description.Container>
                  <Popover
                    placement="bottomLeft"
                    content={deployment.status.endpoint.external_endpoint}
                  >
                    <span>
                      <Hoverable>
                        <Description.Item
                          icon={<CarbonIcon icon={<Api_1 />} />}
                          description={
                            <Typography.Text
                              copyable={{
                                text: deployment.status.endpoint
                                  .external_endpoint,
                                tooltips: false,
                                icon: <CarbonIcon icon={<CopyFile />} />,
                              }}
                            >
                              External Endpoint
                            </Typography.Text>
                          }
                        />
                      </Hoverable>
                    </span>
                  </Popover>
                  <Popover
                    placement="bottomLeft"
                    content={deployment.status.endpoint.internal_endpoint}
                  >
                    <span>
                      <Hoverable>
                        <Description.Item
                          description={
                            <Typography.Text
                              copyable={{
                                text: deployment.status.endpoint
                                  .internal_endpoint,
                                tooltips: false,
                                icon: <CarbonIcon icon={<CopyFile />} />,
                              }}
                            >
                              Internal Endpoint
                            </Typography.Text>
                          }
                        />
                      </Hoverable>
                    </span>
                  </Popover>
                </Description.Container>
              </Col>
            </Row>
          </Col>
          <Col flex="0 0 auto">
            <Row gutter={[0, 4]}>
              <Col span={24}>
                <Description.Item
                  icon={<CarbonIcon icon={<FlowModeler />} />}
                  description={
                    deployment.resource_requirement.accelerator_num ? (
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
              <Col span={24}>
                <Description.Container>
                  <Description.Item
                    icon={<CarbonIcon icon={<MessageQueue />} />}
                    description={`${deployment.resource_requirement.memory} MB`}
                  />
                  <Description.Item
                    icon={<CarbonIcon icon={<Chip />} />}
                    description={`${deployment.resource_requirement.cpu} CORE`}
                  />
                </Description.Container>
              </Col>
              <Col span={24}>
                <Description.Container>
                  <Description.Item
                    icon={<CarbonIcon icon={<Replicate />} />}
                    term="Min Replicas"
                    description={deployment.resource_requirement.min_replicas}
                  />
                  {deployment.envs && deployment.envs.length > 0 ? (
                    <Envs envs={deployment.envs} />
                  ) : null}
                </Description.Container>
              </Col>
            </Row>
          </Col>
        </Row>
      </Col>
    </Row>
  );
};
