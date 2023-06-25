import { css as classNameCss } from "@emotion/css";
import { DateParser } from "@lepton-dashboard/components/date-parser";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { DeploymentStatus } from "@lepton-dashboard/routers/workspace/components/deployment-status";
import { WorkspaceTrackerService } from "@lepton-dashboard/routers/workspace/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { Table } from "antd";
import { FC } from "react";
import { useNavigate } from "react-router-dom";

export const DeploymentMinTable: FC<{ deployments: Deployment[] }> = ({
  deployments,
}) => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const navigate = useNavigate();

  return (
    <Table
      rowClassName={classNameCss`cursor: pointer;`}
      size="small"
      showHeader={false}
      pagination={false}
      bordered
      rowKey="id"
      onRow={(record) => {
        return {
          onClick: () =>
            navigate(
              `/workspace/${workspaceTrackerService.name}/deployments/detail/${record.id}`
            ),
        };
      }}
      columns={[
        {
          title: "Status",
          dataIndex: ["status", "state"],
          render: (state) => <DeploymentStatus status={state} />,
        },
        {
          title: "Name",
          dataIndex: "name",
          render: (v) => v,
        },
        {
          title: "Created",
          dataIndex: "created_at",
          render: (data) => <DateParser detail date={data} />,
        },
      ]}
      dataSource={deployments}
    />
  );
};
