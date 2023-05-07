import { FC } from "react";
import { Card } from "@lepton-dashboard/components/card";
import { App, Button, Col, Divider, Popconfirm, Row, Space } from "antd";
import { Model } from "@lepton-dashboard/interfaces/model.ts";
import { Link } from "@lepton-dashboard/components/link";
import { DeleteOutlined, EyeOutlined, RocketOutlined } from "@ant-design/icons";
import { KeyValue } from "@lepton-dashboard/components/key-value";
import dayjs from "dayjs";
import { useInject } from "@lepton-libs/di";
import { ModelService } from "@lepton-dashboard/services/model.service.ts";
import { RefreshService } from "@lepton-dashboard/services/refresh.service.ts";

export const ModelCard: FC<{
  model?: Model;
  borderless?: boolean;
  shadowless?: boolean;
  paddingless?: boolean;
  detail?: boolean;
  inModel?: boolean;
  action?: boolean;
  id?: boolean;
}> = ({
  model,
  borderless = false,
  paddingless = false,
  shadowless = false,
  detail = false,
  inModel = false,
  action = true,
  id = true,
}) => {
  const { message } = App.useApp();
  const modelService = useInject(ModelService);
  const refreshService = useInject(RefreshService);
  return (
    <Card
      paddingless={paddingless}
      borderless={borderless}
      shadowless={shadowless}
    >
      {model && (
        <Row gutter={16} wrap={true}>
          <Col flex="auto">
            {(detail || inModel) && (
              <KeyValue title="Name" value={model.name} />
            )}
            {id && <KeyValue title="ID" value={model.id} />}
            <KeyValue title="Model source" value={model.model_source || "-"} />
            <KeyValue title="Image URL" value={model.image_url || "-"} />
            <KeyValue
              title="Exposed Ports"
              value={model.exposed_ports?.join(", ") || "-"}
            />
          </Col>
          <Col flex="auto">
            {(detail || inModel) && (
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
            {action && (
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
                        icon={<EyeOutlined />}
                        to={`/models/detail/${model.id}`}
                        relative="route"
                      >
                        Detail
                      </Link>
                    }
                  />
                )}
                <KeyValue
                  value={
                    <Popconfirm
                      title="Delete the model"
                      description="Are you sure to delete?"
                      onConfirm={() => {
                        void message.loading({
                          content: `Deleting model ${model.id}, please wait...`,
                          key: "delete-model",
                          duration: 0,
                        });
                        modelService.delete(model.id).subscribe({
                          next: () => {
                            message.destroy("delete-model");
                            void message.success(
                              `Successfully deleted model ${model.id}`
                            );
                            refreshService.refresh();
                          },
                          error: () => {
                            message.destroy("delete-model");
                          },
                        });
                      }}
                    >
                      <Button
                        type="link"
                        danger
                        style={{ padding: 0 }}
                        icon={<DeleteOutlined />}
                      >
                        Delete
                      </Button>
                    </Popconfirm>
                  }
                />
              </Space>
            )}
          </Col>
        </Row>
      )}
    </Card>
  );
};
