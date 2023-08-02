import { HardwareIndicator } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/hardware-indicator";
import { PhotonIndicator } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/photon-indicator";
import { Storage } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/storage";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { FC } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import {
  App,
  Button,
  Col,
  Divider,
  Popconfirm,
  Row,
  Space,
  Typography,
} from "antd";
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
import { Envs } from "@lepton-dashboard/routers/workspace/components/deployment-item/components/envs";
import { NavigateService } from "@lepton-dashboard/services/navigate.service";
import { LinkTo } from "@lepton-dashboard/components/link-to";

export const DeploymentItem: FC<{ deployment: Deployment }> = ({
  deployment,
}) => {
  const theme = useAntdTheme();
  const { message } = App.useApp();
  const navigateService = useInject(NavigateService);
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
            <LinkTo
              css={css`
                color: ${theme.colorTextHeading};
              `}
              icon={
                <DeploymentStatus
                  deploymentName={deployment.name}
                  status={deployment.status.state}
                />
              }
              name="deploymentDetail"
              params={{ deploymentName: deployment.name }}
              relative="route"
            >
              <Description.Item
                css={css`
                  font-weight: 600;
                  font-size: 16px;
                `}
                term={deployment.name}
              />
            </LinkTo>
          </Col>
          <Col flex="0 0 auto">
            <Space size={0} split={<Divider type="vertical" />}>
              <EditDeployment deployment={deployment} />
              <Popconfirm
                title="Delete the deployment"
                description="Are you sure to delete?"
                disabled={workspaceTrackerService.workspace?.isPastDue}
                onConfirm={() => {
                  void message.loading({
                    content: `Deleting deployment ${deployment.name}, please wait...`,
                    key: "delete-deployment",
                    duration: 0,
                  });
                  deploymentService.delete(deployment.name).subscribe({
                    next: () => {
                      message.destroy("delete-deployment");
                      void message.success(
                        `Successfully deleted deployment ${deployment.name}`
                      );
                      refreshService.refresh();
                      navigateService.navigateTo("deploymentsList", null, {
                        relative: "route",
                      });
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
                  disabled={workspaceTrackerService.workspace?.isPastDue}
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
        <Row gutter={[16, 4]}>
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
                  <Description.Item
                    icon={<CarbonIcon icon={<Api />} />}
                    term="Endpoint"
                    description={
                      <Typography.Text
                        style={{ maxWidth: "280px" }}
                        ellipsis={{ tooltip: true }}
                        copyable={{
                          tooltips: false,
                          icon: <CarbonIcon icon={<CopyFile />} />,
                        }}
                      >
                        {deployment.status.endpoint.external_endpoint}
                      </Typography.Text>
                    }
                  />
                </Description.Container>
              </Col>
            </Row>
          </Col>
          <Col flex="0 0 400px">
            <Row gutter={[0, 4]}>
              <Col span={24}>
                <Description.Container>
                  <Description.Item
                    icon={<CarbonIcon icon={<Replicate />} />}
                    description={
                      <LinkTo
                        name="deploymentDetailReplicasList"
                        params={{ deploymentName: deployment.name }}
                      >
                        {deployment.resource_requirement.min_replicas}
                        {deployment.resource_requirement.min_replicas > 1
                          ? " replicas"
                          : " replica"}
                      </LinkTo>
                    }
                  />
                  {deployment.mounts && deployment.mounts.length > 0 ? (
                    <Storage mounts={deployment.mounts} />
                  ) : null}
                  {deployment.envs && deployment.envs.length > 0 ? (
                    <Envs envs={deployment.envs} />
                  ) : null}
                </Description.Container>
              </Col>
              <Col span={24}>
                <Description.Item
                  icon={<CarbonIcon icon={<Time />} />}
                  description={
                    <>
                      Created at <DateParser date={deployment.created_at} />
                    </>
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
