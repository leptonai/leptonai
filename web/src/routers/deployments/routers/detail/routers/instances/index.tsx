import { FC, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { Card } from "@lepton-dashboard/components/card";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/services/deployment.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { debounceTime, startWith, switchMap, tap } from "rxjs";
import { Divider, Space, Table } from "antd";
import { Terminal } from "@lepton-dashboard/routers/deployments/routers/detail/routers/instances/components/terminal";
import { LogsViewer } from "@lepton-dashboard/routers/deployments/routers/detail/routers/instances/components/logs-viewer";
import { css } from "@emotion/react";
import { Metrics } from "@lepton-dashboard/routers/deployments/routers/detail/routers/instances/components/metrics";

export const Instances: FC = () => {
  const deployment = useOutletContext<Deployment>();
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
    <Card shadowless borderless>
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
                <Metrics instance={instance} deployment={deployment} />
              </Space>
            ),
          },
        ]}
        rowKey="id"
      />
    </Card>
  );
};
