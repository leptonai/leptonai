import { ActionsHeader } from "@lepton-dashboard/components/actions-header";
import { FC, useState } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { useInject } from "@lepton-libs/di";
import { DeploymentService } from "@lepton-dashboard/routers/workspace/services/deployment.service";
import { RefreshService } from "@lepton-dashboard/services/refresh.service";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { combineLatest, map, switchMap, tap } from "rxjs";
import { Card } from "@lepton-dashboard/routers/workspace/components/card";
import { Divider, Space, Table, Tag, Typography } from "antd";
import { Terminal } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/replicas/components/terminal";
import { LogsViewer } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/replicas/components/logs-viewer";
import { Metrics } from "@lepton-dashboard/routers/workspace/routers/detail/routers/deployments/routers/detail/routers/replicas/components/metrics";
import { Link } from "@lepton-dashboard/routers/workspace/components/link";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";

export const List: FC<{
  deployment: Deployment;
}> = ({ deployment }) => {
  const theme = useAntdTheme();
  const deploymentService = useInject(DeploymentService);
  const refreshService = useInject(RefreshService);
  const [loading, setLoading] = useState(true);
  const [hasIssues, setHasIssues] = useState(false);
  const [expandedRowKeys, setExpandedRowKeys] = useState<string[]>([]);
  const replicas = useStateFromObservable(
    () =>
      refreshService.refresh$.pipe(
        switchMap(() =>
          combineLatest([
            deploymentService.getReadiness(deployment.id).pipe(
              tap((readiness) => {
                const hasIssues = Object.entries(readiness).some(([_, value]) =>
                  value.some((e) => !!e.message)
                );
                setHasIssues(hasIssues);
                setExpandedRowKeys((prevState) => {
                  if (!hasIssues) {
                    return [];
                  }
                  return prevState.filter((e) => Object.hasOwn(readiness, e));
                });
              })
            ),
            deploymentService.listReplicas(deployment.id),
          ]).pipe(
            map(([readiness, replicas]) => {
              return replicas
                .map((replica) => {
                  const replicaReadiness = (readiness[replica.id] || [])
                    .filter((e) => !!e.message)
                    .map((e, i) => ({
                      ...e,
                      key: `${replica.id}-readiness-${i}`,
                    }));
                  return {
                    ...replica,
                    issues: replicaReadiness,
                  };
                })
                .sort((a, b) => {
                  if (a.issues.length > b.issues.length) {
                    return -1;
                  }
                  if (a.issues.length < b.issues.length) {
                    return 1;
                  }
                  return 0;
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

  const expand = (expanded: boolean, key: string) => {
    if (expanded) {
      setExpandedRowKeys((prevState) => {
        return [...prevState, key];
      });
    } else {
      setExpandedRowKeys((prevState) => {
        return prevState.filter((e) => e !== key);
      });
    }
  };

  return (
    <Card shadowless borderless>
      <Table
        css={css`
          .ant-table-expanded-row {
            .ant-table-cell,
            &:hover,
            &:hover > td {
              background: ${theme.colorWarningBg} !important;
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
                <Link to={`../detail/${id}`} relative="path">
                  {id}
                </Link>
                {record?.issues.length > 0 && (
                  <Tag
                    css={css`
                      cursor: pointer;
                      user-select: none;
                    `}
                    color="warning"
                    onClick={() => {
                      const expanded = expandedRowKeys.includes(record.id);
                      expand(!expanded, record.id);
                    }}
                  >
                    {record.issues.length}
                    {record.issues.length === 1 ? " issue" : " issues"}
                  </Tag>
                )}
              </Space>
            ),
          },
          {
            ellipsis: true,
            width: 300,
            title: <ActionsHeader />,
            render: (_, replica) => (
              <Space size={0} split={<Divider type="vertical" />}>
                <Terminal replica={replica} deployment={deployment} />
                <LogsViewer replica={replica} deployment={deployment} />
                <Metrics replica={replica} deployment={deployment} />
              </Space>
            ),
          },
        ]}
        expandable={{
          expandedRowKeys,
          showExpandColumn: hasIssues,
          rowExpandable: (record) => record.issues.length > 0,
          onExpand: (expanded, record) => {
            expand(expanded, record.id);
          },
          expandedRowRender: (record) => (
            <Table
              css={css`
                .ant-table {
                  background: transparent;
                }

                .ant-table td {
                  color: ${theme.colorWarningText};
                }

                tr:hover,
                .ant-table-row:hover > td {
                  background: ${theme.colorWarningBg} !important;
                }
              `}
              size="small"
              pagination={false}
              showHeader={false}
              dataSource={record.issues}
              columns={[
                {
                  title: "Message",
                  dataIndex: "message",
                  ellipsis: true,
                },
                {
                  title: "action",
                  dataIndex: "key",
                  width: 40,
                  render: (_, record) => (
                    <Typography.Text copyable={{ text: record.message }} />
                  ),
                },
              ]}
            />
          ),
        }}
      />
    </Card>
  );
};
