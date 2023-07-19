import { css as classNameCss } from "@emotion/css";
import { DateParser } from "@lepton-dashboard/components/date-parser";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { DeploymentStatus } from "@lepton-dashboard/routers/workspace/components/deployment-status";
import { useInject } from "@lepton-libs/di";
import { Table } from "antd";
import { FC } from "react";
import { NavigateService } from "@lepton-dashboard/services/navigate.service";

export const DeploymentMinTable: FC<{ deployments: Deployment[] }> = ({
  deployments,
}) => {
  const navigateService = useInject(NavigateService);

  return (
    <Table
      rowClassName={classNameCss`cursor: pointer;`}
      size="small"
      showHeader={false}
      pagination={false}
      bordered
      rowKey="name"
      onRow={(record) => {
        return {
          onClick: () =>
            navigateService.navigateTo("deploymentDetail", {
              deploymentName: record.name,
            }),
        };
      }}
      columns={[
        {
          title: "Status",
          dataIndex: ["status", "state"],
          render: (state, record) => (
            <DeploymentStatus deploymentName={record.name} status={state} />
          ),
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
