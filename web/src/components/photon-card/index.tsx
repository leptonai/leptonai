import { FC } from "react";
import { Card } from "@lepton-dashboard/components/card";
import { App, Button, Col, Divider, Popconfirm, Row, Space } from "antd";
import { Photon } from "@lepton-dashboard/interfaces/photon.ts";
import { Link } from "@lepton-dashboard/components/link";
import { DeleteOutlined, EyeOutlined, RocketOutlined } from "@ant-design/icons";
import { KeyValue } from "@lepton-dashboard/components/key-value";
import dayjs from "dayjs";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/services/photon.service.ts";
import { RefreshService } from "@lepton-dashboard/services/refresh.service.ts";

export const PhotonCard: FC<{
  photon?: Photon;
  borderless?: boolean;
  shadowless?: boolean;
  paddingless?: boolean;
  detail?: boolean;
  inPhoton?: boolean;
  action?: boolean;
  id?: boolean;
}> = ({
  photon,
  borderless = false,
  paddingless = false,
  shadowless = false,
  detail = false,
  inPhoton = false,
  action = true,
  id = true,
}) => {
  const { message } = App.useApp();
  const photonService = useInject(PhotonService);
  const refreshService = useInject(RefreshService);
  return (
    <Card
      paddingless={paddingless}
      borderless={borderless}
      shadowless={shadowless}
    >
      {photon && (
        <Row gutter={16} wrap={true}>
          <Col flex="auto">
            {(detail || inPhoton) && (
              <KeyValue title="Name" value={photon.name} />
            )}
            {id && <KeyValue title="ID" value={photon.id} />}
            <KeyValue title="Model" value={photon.model || "-"} />
            <KeyValue
              title="Exposed Ports"
              value={photon.exposed_ports?.join(", ") || "-"}
            />
            <KeyValue
              title="Requirements"
              value={photon.requirement_dependency?.join(", ") || "-"}
            />
          </Col>
          <Col flex="auto">
            {(detail || inPhoton) && (
              <KeyValue
                title="Create Time"
                value={dayjs(photon.created_at).format("lll")}
              />
            )}
            <KeyValue title="Image URL" value={photon.image || "-"} />
            <KeyValue
              title="Container Args"
              value={photon.container_args?.join(", ") || "-"}
            />
            <KeyValue title="Entrypoint" value={photon.entrypoint || "-"} />
            {action && (
              <Space split={<Divider type="vertical" />}>
                <KeyValue
                  value={
                    <Link
                      icon={<RocketOutlined />}
                      to={`/deployments/create/${photon.id}`}
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
                        to={`/photons/detail/${photon.id}`}
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
                      title="Delete the photon"
                      description="Are you sure to delete?"
                      onConfirm={() => {
                        void message.loading({
                          content: `Deleting photon ${photon.id}, please wait...`,
                          key: "delete-photon",
                          duration: 0,
                        });
                        photonService.delete(photon.id).subscribe({
                          next: () => {
                            message.destroy("delete-photon");
                            void message.success(
                              `Successfully deleted photon ${photon.id}`
                            );
                            refreshService.refresh();
                          },
                          error: () => {
                            message.destroy("delete-photon");
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
