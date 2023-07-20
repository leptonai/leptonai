import { ActionsHeader } from "@lepton-dashboard/components/actions-header";
import { FC, useMemo, useState } from "react";
import {
  Deployment,
  DeploymentReadinessItem,
  ReadinessReason,
  Replica,
  ReplicaTermination,
} from "@lepton-dashboard/interfaces/deployment";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { combineLatest, map, switchMap } from "rxjs";
import { Card } from "@lepton-dashboard/components/card";
import { Divider, Space, Table, Tag, Typography } from "antd";
import { Terminal } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/replicas/components/terminal";
import { LogsViewer } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/replicas/components/logs-viewer";
import { Metrics } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/replicas/components/metrics";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { LinkTo } from "@lepton-dashboard/components/link-to";
import {
  StatusPopover,
  TerminationsPopover,
} from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/replicas/routers/list/components/status-popover";

interface UIReplica extends Replica {
  status: Status;
  readiness?: (DeploymentReadinessItem & { key: string })[];
  terminations?: (ReplicaTermination & { key: string })[];
}
type Status = "terminated" | "ready" | "pending" | "unknown";

const ReplicaStatusTag = ({ status }: { status: Status }) => {
  const color = useMemo(() => {
    switch (status) {
      case "ready":
        return "success";
      case "pending":
        return "processing";
      case "terminated":
        return "default";
      default:
        return "default";
    }
  }, [status]);
  const text = useMemo(() => {
    switch (status) {
      case "ready":
        return "READY";
      case "pending":
        return "PENDING";
      case "terminated":
        return "TERMINATED";
      default:
        return "UNKNOWN";
    }
  }, [status]);

  return (
    <Tag
      css={css`
        width: 90px;
        text-align: center;
      `}
      color={color}
    >
      {text}
    </Tag>
  );
};

export const List: FC<{
  deployment: Deployment;
}> = ({ deployment }) => {
  const theme = useAntdTheme();
  const deploymentService = useInject(DeploymentService);
  const refreshService = useInject(RefreshService);
  const [loading, setLoading] = useState(true);
  const replicas: UIReplica[] = useStateFromObservable(
    () =>
      refreshService.refresh$.pipe(
        switchMap(() =>
          combineLatest([
            deploymentService.getReadiness(deployment.name),
            deploymentService.listReplicas(deployment.name),
            deploymentService.getTerminations(deployment.name),
          ]).pipe(
            map(([readiness, replicas, terminations]) => {
              const mixedReadiness: UIReplica[] = replicas.map((e) => ({
                ...e,
                status: "unknown",
              }));
              Object.entries(terminations).forEach(([key]) => {
                const existing = mixedReadiness.find((e) => e.id === key);
                if (!existing) {
                  mixedReadiness.push({
                    id: key,
                    // If it doesn't exist in replicas but in terminations, its status is terminated.
                    status: "terminated",
                  });
                }
              });

              return mixedReadiness.map((replica) => {
                const replicaReadiness = (readiness[replica.id] || []).map(
                  (e, i) => ({
                    ...e,
                    key: `${replica.id}-readiness-${i}`,
                  })
                );

                const replicaTerminations = (
                  terminations[replica.id] || []
                ).map((e, i) => {
                  return {
                    ...e,
                    key: `${replica.id}-termination-${i}`,
                  };
                });

                const isReady = (readiness[replica.id] || []).every(
                  (e) => e.reason === ReadinessReason.ReadinessReasonReady
                );
                const status: Status = (() => {
                  if (isReady) {
                    return "ready";
                  }
                  return "pending";
                })();
                return {
                  ...replica,
                  status,
                  readiness: replicaReadiness,
                  terminations: replicaTerminations,
                };
              });
            })
          )
        )
      ),
    [],
    {
      next: () => setLoading(false),
      error: () => setLoading(false),
    }
  );

  return (
    <Card shadowless borderless>
      <Table
        scroll={{ y: "800px" }}
        css={css`
          .ant-table-expanded-row {
            .ant-table-cell,
            &:hover,
            &:hover > td {
              background: ${theme.controlItemBgActiveHover} !important;
            }
          }
        `}
        loading={loading}
        pagination={false}
        size="small"
        dataSource={replicas}
        bordered
        tableLayout="fixed"
        rowKey="id"
        columns={[
          {
            dataIndex: "id",
            title: "ID",
            ellipsis: true,
            render: (id, record) => (
              <Space>
                <StatusPopover readiness={record.readiness}>
                  <ReplicaStatusTag status={record.status} />
                </StatusPopover>
                {record.status === "terminated" ? (
                  <Typography.Text type="secondary">{id}</Typography.Text>
                ) : (
                  <LinkTo
                    name="deploymentDetailReplicasDetail"
                    params={{
                      deploymentName: deployment.name,
                      replicaId: id,
                    }}
                    relative="path"
                  >
                    {id}
                  </LinkTo>
                )}
                {!!record.terminations && record.terminations?.length > 0 && (
                  <TerminationsPopover terminations={record.terminations}>
                    <Typography.Text
                      css={css`
                        cursor: pointer;
                      `}
                      type="secondary"
                      underline
                    >
                      {record.terminations.length} terminated
                    </Typography.Text>
                  </TerminationsPopover>
                )}
              </Space>
            ),
          },
          {
            ellipsis: true,
            title: <ActionsHeader />,
            render: (_, replica) => (
              <Space size={0} split={<Divider type="vertical" />}>
                <Terminal
                  replica={replica}
                  deployment={deployment}
                  disabled={replica.status === "terminated"}
                />
                <LogsViewer
                  replica={replica}
                  deployment={deployment}
                  disabled={replica.status === "terminated"}
                />
                <Metrics
                  replica={replica}
                  deployment={deployment}
                  disabled={replica.status === "terminated"}
                />
              </Space>
            ),
          },
        ]}
      />
    </Card>
  );
};
