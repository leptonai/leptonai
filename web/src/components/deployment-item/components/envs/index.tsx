import { FC } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { Description } from "@lepton-dashboard/components/description";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ListDropdown } from "@carbon/icons-react";
import { Hoverable } from "@lepton-dashboard/components/hoverable";
import { Popover, Table } from "antd";

export const Envs: FC<{ envs: Deployment["envs"] }> = ({ envs }) => {
  if (envs && envs.length > 0) {
    return (
      <Popover
        placement="bottomLeft"
        content={
          <Table
            size="small"
            pagination={false}
            bordered
            rowKey="name"
            columns={[
              {
                title: "Env name",
                dataIndex: "name",
              },
              {
                title: "Env value",
                dataIndex: "value",
              },
            ]}
            dataSource={envs}
          />
        }
      >
        <span>
          <Hoverable>
            <Description.Item
              icon={<CarbonIcon icon={<ListDropdown />} />}
              description="Env Variable"
            />
          </Hoverable>
        </span>
      </Popover>
    );
  } else {
    return null;
  }
};
