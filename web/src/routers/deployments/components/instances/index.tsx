import { FC, useState } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { debounceTime, startWith, switchMap, tap } from "rxjs";
import { Divider, Space, Table } from "antd";
import { css } from "@emotion/react";
import { LogsViewer } from "@lepton-dashboard/routers/deployments/components/instances/components/logs-viewer";
import { Terminal } from "@lepton-dashboard/routers/deployments/components/instances/components/terminal";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";

export const Instances: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const deploymentService = useInject(DeploymentService);
  const refreshService = useInject(RefreshService);
  const [loading, setLoading] = useState(true);
  const instances = useStateFromObservable(
    () =>
      refreshService.refresh$.pipe(
        startWith(true),
        debounceTime(300),
        switchMap(() =>
          deploymentService
            .listInstances(deployment.id)
            .pipe(tap(() => setLoading(false)))
        )
      ),
    []
  );
  return (
    <Table
      loading={loading}
      pagination={false}
      size="small"
      dataSource={instances}
      bordered
      columns={[
        { dataIndex: "id", title: "ID" },
        {
          title: (
            <div
              css={css`
                margin-left: 8px;
              `}
            >
              Actions
            </div>
          ),
          render: (_, instance) => (
            <Space split={<Divider type="vertical" />}>
              <Terminal instance={instance} deployment={deployment} />
              <LogsViewer instance={instance} deployment={deployment} />
            </Space>
          ),
        },
      ]}
      rowKey="id"
    />
  );
};
