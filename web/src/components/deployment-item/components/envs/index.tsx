import { FC } from "react";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { Description } from "@lepton-dashboard/components/description";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ListDropdown } from "@carbon/icons-react";
import { Hoverable } from "@lepton-dashboard/components/hoverable";
import { Popover, Table } from "antd";
import { css } from "@emotion/react";

export const Envs: FC<{ envs: Deployment["envs"] }> = ({ envs }) => {
  if (envs && envs.length > 0) {
    return (
      <Popover
        placement="bottomLeft"
        content={
          <Table
            css={css`
              width: 400px;
              max-width: 80vw;
            `}
            size="small"
            pagination={false}
            bordered
            rowKey="name"
            columns={[
              {
                ellipsis: true,
                title: "Env name",
                dataIndex: "name",
              },
              {
                width: "60%",
                ellipsis: true,
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
