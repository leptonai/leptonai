import { Asterisk } from "@carbon/icons-react";
import { ActionsHeader } from "@lepton-dashboard/components/actions-header";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Link } from "@lepton-dashboard/components/link";
import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { Secret } from "@lepton-dashboard/interfaces/secret";
import { Card } from "@lepton-dashboard/components/card";
import { DeleteSecret } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/secrets/components/delete-secret";
import { EditSecret } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/secrets/components/edit-secret";
import { NewSecret } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/secrets/components/new-secret";
import { SecretService } from "@lepton-dashboard/routers/workspace/services/secret.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Divider, Empty, Space, Table } from "antd";
import { ColumnsType } from "antd/es/table";
import { FC, useState } from "react";
import { switchMap } from "rxjs";

export const Secrets: FC = () => {
  const [loading, setLoading] = useState(true);
  const refreshService = useInject(RefreshService);
  const secretService = useInject(SecretService);
  useDocumentTitle("Secrets");
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
          <DeleteSecret secret={name} />
        </Space>
      ),
    },
  ];

  return (
    <Card
      loading={loading}
      borderless
      icon={<CarbonIcon icon={<Asterisk />} />}
      title="Secrets"
      extra={<NewSecret afterAction={() => refreshService.refresh()} />}
    >
      <Table
        bordered
        pagination={false}
        size="small"
        columns={columns}
        dataSource={secrets}
        rowKey="name"
        locale={{
          emptyText: (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={
                <>
                  <Link
                    to="https://www.lepton.ai/docs/advanced/env_n_secrets"
                    target="_blank"
                  >
                    No data, learn more about secrets
                  </Link>
                </>
              }
            />
          ),
        }}
      />
    </Card>
  );
};