import { Link } from "@lepton-dashboard/routers/workspace/components/link";
import { WorkspaceTrackerService } from "@lepton-dashboard/routers/workspace/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { FC } from "react";
import {
  Deployment,
  DeploymentSecretEnv,
} from "@lepton-dashboard/interfaces/deployment";
import { Description } from "@lepton-dashboard/routers/workspace/components/description";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Asterisk, ListDropdown } from "@carbon/icons-react";
import { Hoverable } from "@lepton-dashboard/routers/workspace/components/hoverable";
import { Popover, Table, Tag, Typography } from "antd";
import { css } from "@emotion/react";

export const Envs: FC<{ envs: Deployment["envs"] }> = ({ envs }) => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  if (envs && envs.length > 0) {
    return (
      <Popover
        placement="bottomLeft"
        content={
          <Table
            css={css`
              width: 300px;
              max-width: 80vw;
            `}
            size="small"
            pagination={false}
            bordered
            rowKey="name"
            showHeader={false}
            columns={[
              {
                ellipsis: true,
                title: "Env name",
                dataIndex: "name",
                render: (v) => <Typography.Text strong>{v}</Typography.Text>,
              },
              {
                width: "60%",
                ellipsis: true,
                title: "Env value",
                dataIndex: "value",
                render: (value, data) => {
                  const secretRef = (data as DeploymentSecretEnv)?.value_from
                    ?.secret_name_ref;
                  if (secretRef) {
                    return (
                      <Link
                        to={`/workspace/${workspaceTrackerService.name}/secrets`}
                      >
                        <Tag
                          color="default"
                          icon={<CarbonIcon icon={<Asterisk />} />}
                        >
                          {secretRef}
                        </Tag>
                      </Link>
                    );
                  } else {
                    return value;
                  }
                },
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
              description="Secret & Variables"
            />
          </Hoverable>
        </span>
      </Popover>
    );
  } else {
    return null;
  }
};
