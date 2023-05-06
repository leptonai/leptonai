import { FC } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment.ts";
import { Card } from "@lepton-dashboard/components/card";
import { Badge, Col, Divider, Row, Space, Tooltip, Typography } from "antd";
import dayjs from "dayjs";
import { Link } from "@lepton-dashboard/components/link";
import { css } from "@emotion/react";
import { Hoverable } from "@lepton-dashboard/components/hoverable";
import { KeyValue } from "@lepton-dashboard/routers/deployments/components/key-value";
import { CloseOutlined, EditOutlined, EyeOutlined } from "@ant-design/icons";

export const DeploymentCard: FC<{ deployment: Deployment }> = ({
  deployment,
}) => {
  return (
    <Card borderless>
      <Row gutter={16}>
        <Col flex="1 1 auto">
          <KeyValue
            value={
              <Link to={`../detail/${deployment.id}/mode/view`}>
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
        </Col>
        <Col flex="350px">
          <KeyValue
            value={
              <Badge
                status={
                  deployment.status.state === "running"
                    ? "success"
                    : "processing"
                }
                text={deployment.status.state.toUpperCase()}
              />
            }
          />
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
        </Col>
        <Col flex="450px">
          <Space split={<Divider type="vertical" />}>
            <KeyValue
              title="Min Replicas"
              value={deployment.resource_requirement.min_replicas}
            />
            <KeyValue
              title="MEM"
              value={`${deployment.resource_requirement.memory} MB`}
            />
            <KeyValue title="CPU" value={deployment.resource_requirement.cpu} />
          </Space>
          <KeyValue
            title="Accelerator"
            value={
              <>
                {deployment.resource_requirement.accelerator_type}
                <CloseOutlined
                  css={css`
                    margin: 0 4px;
                  `}
                />
                {deployment.resource_requirement.accelerator_num}
              </>
            }
          />
        </Col>
        <Col flex="300px">
          <KeyValue
            title="Created Time"
            value={dayjs(deployment.created_at).format("lll")}
          />
          <Space split={<Divider type="vertical" />}>
            <KeyValue
              value={
                <Link
                  icon={<EyeOutlined />}
                  to={`../detail/${deployment.id}/mode/view`}
                >
                  View
                </Link>
              }
            />
            <KeyValue
              value={
                <Link
                  icon={<EditOutlined />}
                  to={`../detail/${deployment.id}/mode/edit`}
                >
                  Edit
                </Link>
              }
            />
          </Space>
        </Col>
      </Row>
    </Card>
  );
};
