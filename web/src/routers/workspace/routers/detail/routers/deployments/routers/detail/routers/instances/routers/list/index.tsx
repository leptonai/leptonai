import { FC, useState } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { debounceTime, startWith, switchMap, tap } from "rxjs";
import { Card } from "@lepton-dashboard/routers/workspace/components/card";
import { Divider, Space, Table } from "antd";
import { css } from "@emotion/react";
import { Terminal } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/instances/components/terminal";
import { LogsViewer } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/instances/components/logs-viewer";
import { Metrics } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/instances/components/metrics";
import { Link } from "@lepton-dashboard/routers/workspace/components/link";

export const List: FC<{ deployment: Deployment }> = ({ deployment }) => {
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
        tableLayout="fixed"
        columns={[
          {
            dataIndex: "id",
            title: "ID",
            ellipsis: true,
            render: (id) => (
              <Link to={`../detail/${id}`} relative="path">
                {id}
              </Link>
            ),
          },
          {
            ellipsis: true,
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
              <Space size={0} split={<Divider type="vertical" />}>
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
