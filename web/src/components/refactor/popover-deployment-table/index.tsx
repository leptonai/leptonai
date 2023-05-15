import { FC } from "react";
import { Popover, Table, Tag } from "antd";
import { Deployment } from "@lepton-dashboard/interfaces/deployment.ts";
import { Photon } from "@lepton-dashboard/interfaces/photon.ts";
import { DateParser } from "../date-parser";
import { DeploymentStatus } from "@lepton-dashboard/components/refactor/deployment-status";
import { useNavigate } from "react-router-dom";
import { css as classNameCss } from "@emotion/css";
import { Link } from "@lepton-dashboard/components/link";
import { DeploymentIcon } from "@lepton-dashboard/components/icons";
import { Description } from "@lepton-dashboard/components/refactor/description";

export const PopoverDeploymentTable: FC<{
  photon: Photon;
  deployments: Deployment[];
}> = ({ photon, deployments }) => {
  const navigate = useNavigate();
  return (
    <Tag
      color={
        deployments.some((d) => d.status.state === "Running")
          ? "success"
          : "default"
      }
    >
      <Description.Item
        icon={<DeploymentIcon />}
        description={
          <Popover
            open={deployments.length > 0 ? undefined : false}
            placement="bottomLeft"
            content={
              <Table
                rowClassName={classNameCss`cursor: pointer;`}
                size="small"
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
                    render: (data) => <DateParser date={data} />,
                  },
                ]}
                dataSource={deployments}
              />
            }
          >
            <span>
              <Link to={`/deployments/list/${photon.name}`} relative="route">
                {deployments.length > 0 ? deployments.length : "No"}{" "}
                {deployments.length > 1 ? "deployments" : "deployment"}
              </Link>
            </span>
          </Popover>
        }
      />
    </Tag>
  );
};
