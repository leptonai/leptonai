import { FC } from "react";
import { Card } from "@lepton-dashboard/components/card";
import { Col, Divider, Row, Space } from "antd";
import { Model } from "@lepton-dashboard/interfaces/model.ts";
import { Link } from "@lepton-dashboard/components/link";
import { EditOutlined, RocketOutlined } from "@ant-design/icons";
import { KeyValue } from "@lepton-dashboard/components/key-value";
import dayjs from "dayjs";

export const ModelCard: FC<{
  model: Model;
  borderless?: boolean;
  shadowless?: boolean;
  detail?: boolean;
}> = ({ model, borderless = false, shadowless = false, detail = false }) => {
  return (
    <Card borderless={borderless} shadowless={shadowless}>
      <Row gutter={16} wrap={true}>
        <Col flex="auto">
          {detail && <KeyValue title="Name" value={model.name} />}
          <KeyValue title="ID" value={model.id} />
          <KeyValue title="Model source" value={model.model_source} />
          <KeyValue title="Image URL" value={model.image_url} />
          <KeyValue
            title="Exposed Ports"
            value={model.exposed_ports?.join(", ") || "-"}
          />
        </Col>
        <Col flex="auto">
          {detail && (
            <KeyValue
              title="Create Time"
              value={dayjs(model.created_at).format("lll")}
            />
          )}
          <KeyValue
            title="Requirements"
            value={model.requirement_dependency?.join(", ") || "-"}
          />
          <KeyValue
            title="Container Args"
            value={model.container_args?.join(", ") || "-"}
          />
          <KeyValue title="Entrypoint" value={model.entrypoint || "-"} />
          <Space split={<Divider type="vertical" />}>
            <KeyValue
              value={
                <Link
                  icon={<RocketOutlined />}
                  to={`/deployments/create/${model.id}`}
                  relative="route"
                >
                  Deploy
                </Link>
              }
            />
            {!detail && (
              <KeyValue
                value={
                  <Link
                    icon={<EditOutlined />}
                    to={`/models/detail/${model.id}`}
                    relative="route"
                  >
                    View
                  </Link>
                }
              />
            )}
          </Space>
        </Col>
      </Row>
    </Card>
  );
};
