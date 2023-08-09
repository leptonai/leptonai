import { FC, useState } from "react";
import { useInject } from "@lepton-libs/di";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { map, switchMap } from "rxjs";
import { ColumnsType } from "antd/es/table";
import { ActionsHeader } from "@lepton-dashboard/components/actions-header";
import { Empty, Table } from "antd";

import { Card } from "@lepton-dashboard/components/card";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ContainerRegistry } from "@carbon/icons-react";
import { Link } from "@lepton-dashboard/components/link";
import { NewRegistry } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/registries/components/new-registry";
import { ImagePullSecretService } from "@lepton-dashboard/routers/workspace/services/image-pull-secret.service";
import { ImagePullSecret } from "@lepton-dashboard/interfaces/image-pull-secrets";
import { DeleteRegistry } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/registries/components/delete-registry";

export const Registries: FC = () => {
  useDocumentTitle("Registries");
  const [loading, setLoading] = useState(true);
  const refreshService = useInject(RefreshService);
  const imagePullSecretService = useInject(ImagePullSecretService);
  const secrets = useStateFromObservable(
    () =>
      refreshService.refresh$.pipe(
        switchMap(() => imagePullSecretService.listImagePullSecrets()),
        map((secrets) => secrets.map((secret) => secret.metadata))
      ),
    [],
    {
      next: () => setLoading(false),
      error: () => setLoading(false),
    }
  );
  const columns: ColumnsType<ImagePullSecret["metadata"]> = [
    {
      title: "Name",
      dataIndex: "name",
    },
    {
      title: <ActionsHeader />,
      width: 100,
      dataIndex: "name",
      render: (name) => <DeleteRegistry name={name} />,
    },
  ];

  return (
    <Card
      borderless
      shadowless
      icon={<CarbonIcon icon={<ContainerRegistry />} />}
      title="Registries"
      extra={<NewRegistry afterAction={() => refreshService.refresh()} />}
    >
      <Table
        loading={loading}
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
                    to="https://www.lepton.ai/docs/advanced/private_docker_registry"
                    target="_blank"
                  >
                    No data, learn more about private docker registry
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
