import { HardwareIndicator } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/hardware-indicator";
import { PhotonIndicator } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/photon-indicator";
import { Hoverable } from "@lepton-dashboard/routers/workspace/components/hoverable";
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
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Api, CopyFile, Replicate, Time, TrashCan } from "@carbon/icons-react";
import { DeploymentStatus } from "@lepton-dashboard/routers/workspace/components/deployment-status";
import { DateParser } from "../../../../components/date-parser";
import { useInject } from "@lepton-libs/di";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";
import { EditDeployment } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/edit-deployment";
import { useNavigate } from "react-router-dom";
import { Envs } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/envs";
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
              icon={
                <DeploymentStatus
                  deploymentId={deployment.id}
                  status={deployment.status.state}
                />
              }
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
                  size="small"
                  icon={<CarbonIcon icon={<TrashCan />} />}
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
                <Space>
                  <PhotonIndicator photon={photon} deployment={deployment} />
                  <HardwareIndicator
                    shape={deployment.resource_requirement.resource_shape}
                  />
                </Space>
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
                          icon={<CarbonIcon icon={<Api />} />}
                          description={
                            <Typography.Text
                              copyable={{
                                text: deployment.status.endpoint
                                  .external_endpoint,
                                tooltips: false,
                                icon: <CarbonIcon icon={<CopyFile />} />,
                              }}
                            >
                              External endpoint
                            </Typography.Text>
                          }
                        />
                      </Hoverable>
                    </span>
                  </Popover>
                  {deployment.envs && deployment.envs.length > 0 ? (
                    <Envs envs={deployment.envs} />
                  ) : null}
                </Description.Container>
              </Col>
            </Row>
          </Col>
          <Col flex="0 0 auto">
            <Row gutter={[0, 4]}>
              <Col span={24}>
                <Description.Container>
                  <Description.Item
                    icon={<CarbonIcon icon={<Replicate />} />}
                    description={
                      <Link
                        to={`/workspace/${workspaceTrackerService.name}/deployments/detail/${deployment.id}/replicas/list`}
                      >
                        {deployment.resource_requirement.min_replicas}
                        {deployment.resource_requirement.min_replicas > 1
                          ? " replicas"
                          : " replica"}
                      </Link>
                    }
                  />
                </Description.Container>
              </Col>
              <Col span={24}>
                <Description.Item
                  icon={<CarbonIcon icon={<Time />} />}
                  description={
                    <DateParser detail date={deployment.created_at} />
                  }
                />
              </Col>
            </Row>
          </Col>
        </Row>
      </Col>
    </Row>
  );
};
