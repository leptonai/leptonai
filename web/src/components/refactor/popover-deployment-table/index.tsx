import { FC } from "react";
import { Popover, Table } from "antd";
import { Deployment } from "@lepton-dashboard/interfaces/deployment.ts";
import { Photon } from "@lepton-dashboard/interfaces/photon.ts";
import { DataParser } from "@lepton-dashboard/components/refactor/data-parser";
import { DeploymentStatus } from "@lepton-dashboard/components/refactor/deployment-status";
import { useNavigate } from "react-router-dom";
import { css as classNameCss } from "@emotion/css";
import { Link } from "@lepton-dashboard/components/link";

export const PopoverDeploymentTable: FC<{
  photon: Photon;
  deployments: Deployment[];
}> = ({ photon, deployments }) => {
  const navigate = useNavigate();
  return (
    <Popover
      open={deployments.length > 0 ? undefined : false}
      overlayInnerStyle={{ padding: "2px" }}
      placement="bottomLeft"
      content={
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
                navigate(`/deployments/detail/${record.id}/mode/view`),
            };
          }}
          columns={[
            {
              dataIndex: ["status", "state"],
              render: (state) => <DeploymentStatus status={state} />,
            },
            {
              dataIndex: "name",
              render: (v) => v,
            },
            {
              dataIndex: "created_at",
              render: (data) => <DataParser date={data} />,
            },
          ]}
          dataSource={deployments}
        />
      }
    >
      <span>
        <Link
          underline={false}
          to={`/deployments/list/${photon.name}`}
          relative="route"
        >
          {deployments.length > 0 ? deployments.length : "No"}{" "}
          {deployments.length > 1 ? "deployments" : "deployment"}
        </Link>
      </span>
    </Popover>
  );
};
