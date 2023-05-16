import { FC } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment.ts";
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
import { Link } from "@lepton-dashboard/components/link";
import { css } from "@emotion/react";
import { Description } from "@lepton-dashboard/components/description";
import { CarbonIcon, PhotonIcon } from "@lepton-dashboard/components/icons";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import {
  Api_1,
  Chip,
  Edit,
  FlowModeler,
  MessageQueue,
  Replicate,
  Time,
} from "@carbon/icons-react";
import { CloseOutlined, DeleteOutlined } from "@ant-design/icons";
import { DeploymentStatus } from "@lepton-dashboard/components/deployment-status";
import { DateParser } from "@lepton-dashboard/components/date-parser";
import { useInject } from "@lepton-libs/di";
import { RefreshService } from "@lepton-dashboard/services/refresh.service.ts";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service.ts";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable.ts";
import { PhotonService } from "@lepton-dashboard/services/photon.service.ts";
import { PhotonItem } from "@lepton-dashboard/components/photon-item";
import { useNavigate } from "react-router-dom";
import { Hoverable } from "@lepton-dashboard/components/hoverable";

export const DeploymentItem: FC<{ deployment: Deployment }> = ({
  deployment,
}) => {
  const theme = useAntdTheme();
  const { message } = App.useApp();
  const refreshService = useInject(RefreshService);
  const deploymentService = useInject(DeploymentService);
  const photonService = useInject(PhotonService);
  const photon = useStateFromObservable(
    () => photonService.id(deployment.photon_id),
    undefined
  );
  const navigate = useNavigate();
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
              to={`/deployments/detail/${deployment.id}/mode/view`}
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
              <Button
                type="text"
                size="small"
                icon={<CarbonIcon icon={<Edit />} />}
                onClick={() =>
                  navigate(`/deployments/detail/${deployment.id}/mode/edit`)
                }
              >
                Edit
              </Button>
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
        <Row>
          <Col flex="0 0 400px">
            <Row gutter={[0, 4]}>
              <Col span={24}>
                <Description.Item
                  icon={<PhotonIcon />}
                  description={
                    photon?.name ? (
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
                    content={
                      <Typography.Text copyable>
                        {deployment.status.endpoint.external_endpoint}
                      </Typography.Text>
                    }
                  >
                    <span>
                      <Hoverable>
                        <Description.Item
                          icon={<CarbonIcon icon={<Api_1 />} />}
                          description="External Endpoint"
                        />
                      </Hoverable>
                    </span>
                  </Popover>
                  <Popover
                    placement="bottomLeft"
                    content={
                      <Typography.Text copyable>
                        {deployment.status.endpoint.internal_endpoint}
                      </Typography.Text>
                    }
                  >
                    <span>
                      <Hoverable>
                        <Description.Item
                          icon={<CarbonIcon icon={<Api_1 />} />}
                          description="Internal Endpoint"
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
                  icon={<CarbonIcon icon={<Replicate />} />}
                  term="Min Replicas"
                  description={deployment.resource_requirement.min_replicas}
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
                <Description.Item
                  icon={<CarbonIcon icon={<FlowModeler />} />}
                  description={
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
            </Row>
          </Col>
        </Row>
      </Col>
    </Row>
  );
};
