import { Asterisk, TrashCan } from "@carbon/icons-react";
import { ActionsHeader } from "@lepton-dashboard/components/actions-header";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Secret } from "@lepton-dashboard/interfaces/secret";
import { Card } from "@lepton-dashboard/routers/workspace/components/card";
import { EditSecret } from "@lepton-dashboard/routers/workspace/routers/detail/routers/secrets/components/edit-secret";
import { NewSecret } from "@lepton-dashboard/routers/workspace/routers/detail/routers/secrets/components/new-secret";
import { SecretService } from "@lepton-dashboard/routers/workspace/services/secret.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { App, Button, Divider, Popconfirm, Space, Table } from "antd";
import { ColumnsType } from "antd/es/table";
import { FC, useState } from "react";
import { switchMap } from "rxjs";

export const Secrets: FC = () => {
  const [loading, setLoading] = useState(true);
  const { message } = App.useApp();

  const refreshService = useInject(RefreshService);
  const secretService = useInject(SecretService);
  const secrets = useStateFromObservable(
    () =>
      refreshService.refresh$.pipe(
        switchMap(() => secretService.listSecrets())
      ),
    [],
    {
      next: () => setLoading(false),
      error: () => setLoading(false),
    }
  );
  const columns: ColumnsType<Secret> = [
    {
      title: "Name",
      dataIndex: "name",
    },
    {
      title: <ActionsHeader />,
      dataIndex: "name",
      render: (name: string, value) => (
        <Space size={0} split={<Divider type="vertical" />}>
          <EditSecret
            afterAction={() => refreshService.refresh()}
            secret={value}
          />
          <Popconfirm
            title="Delete the secret"
            description="Are you sure to delete?"
            onConfirm={() => {
              void message.loading({
                content: `Deleting secret ${name}, please wait...`,
                key: "delete-secret",
                duration: 0,
              });
              secretService.deleteSecret(name).subscribe({
                next: () => {
                  message.destroy("delete-secret");
                  void message.success(`Successfully deleted secret ${name}`);
                  refreshService.refresh();
                },
                error: () => {
                  message.destroy("delete-secret");
                },
              });
            }}
          >
            <Button
              type="text"
              size="small"
              danger
              icon={<CarbonIcon icon={<TrashCan />} />}
            >
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      icon={<CarbonIcon icon={<Asterisk />} />}
      title="Secrets"
      extra={<NewSecret afterAction={() => refreshService.refresh()} />}
    >
      <Table
        loading={loading}
        bordered
        pagination={false}
        size="small"
        columns={columns}
        dataSource={secrets}
        rowKey="name"
      />
    </Card>
  );
};
