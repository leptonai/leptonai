import { FC, useState } from "react";
import {
  Deployment,
  DeploymentEventTypes,
} from "@lepton-dashboard/interfaces/deployment";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { switchMap, tap } from "rxjs";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { ConfigProvider, Empty, Table, Tag } from "antd";
import { Card } from "../../../../../../../../../../components/card";
import dayjs from "dayjs";

export const Events: FC<{ deployment: Deployment }> = ({ deployment }) => {
  const deploymentService = useInject(DeploymentService);
  const refreshService = useInject(RefreshService);
  const [loading, setLoading] = useState(true);

  const events = useStateFromObservable(
    () =>
      refreshService.refresh$.pipe(
        switchMap(() =>
          deploymentService
            .listEvents(deployment.name)
            .pipe(tap(() => setLoading(false)))
        )
      ),
    []
  );

  return (
    <Card borderless>
      <ConfigProvider
        renderEmpty={() => (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="No events in the past 1 hour"
          />
        )}
      >
        <Table
          loading={loading}
          pagination={false}
          size="small"
          dataSource={events}
          bordered
          tableLayout="fixed"
          footer={events.length ? () => "Events in the past 1 hour" : undefined}
          columns={[
            {
              dataIndex: "type",
              title: "Type",
              ellipsis: true,
              width: 100,
              filters: [
                {
                  text: "Normal",
                  value: DeploymentEventTypes.Normal,
                },
                {
                  text: "Warning",
                  value: DeploymentEventTypes.Warning,
                },
              ],
              render: (type) => {
                switch (type) {
                  case DeploymentEventTypes.Normal:
                    return <Tag color="default">Normal</Tag>;
                  case DeploymentEventTypes.Warning:
                    return <Tag color="warning">Warning</Tag>;
                  default:
                    return <Tag color="default">{type}</Tag>;
                }
              },
            },
            {
              dataIndex: "last_observed_time",
              title: "Time",
              ellipsis: true,
              width: 200,
              sorter: (a, b) =>
                dayjs(a.last_observed_time).valueOf() -
                dayjs(b.last_observed_time).valueOf(),
              render: (time) => dayjs(time).format("YYYY-MM-DD HH:mm:ss"),
            },
            {
              dataIndex: "reason",
              title: "Reason",
              ellipsis: true,
            },
          ]}
        />
      </ConfigProvider>
    </Card>
  );
};
