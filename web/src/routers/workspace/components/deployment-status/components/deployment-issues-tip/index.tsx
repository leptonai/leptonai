import { FC, PropsWithChildren } from "react";
import { Popover, Table } from "antd";
import {
  DeploymentReadiness,
  DeploymentReadinessIssue,
  State,
} from "@lepton-dashboard/interfaces/deployment";
import { css } from "@emotion/react";

const flattenDeploymentReadiness = (
  readiness: DeploymentReadiness
): Array<DeploymentReadinessIssue & { replicaID: string }> => {
  return Object.entries(readiness).reduce(
    (acc, [replicaID, value]) => [
      ...acc,
      ...value.map((v, i) => ({ key: `${replicaID}-${i}`, replicaID, ...v })),
    ],
    [] as Array<DeploymentReadinessIssue & { replicaID: string }>
  );
};

export const DeploymentIssuesTip: FC<
  { status: string; readiness: DeploymentReadiness } & PropsWithChildren
> = ({ status, readiness = {}, children }) => {
  if (status === State.NotReady && Object.keys(readiness).length > 0) {
    const dataSource = flattenDeploymentReadiness(readiness);
    return (
      <Popover
        placement="bottomLeft"
        content={
          <div
            onClick={(e) => e.stopPropagation()}
            css={css`
              width: 500px;
              overflow-y: auto;

              tbody tr td {
                font-size: 12px;
              }
            `}
          >
            <Table
              pagination={false}
              scroll={{ y: 300 }}
              size="small"
              dataSource={dataSource}
              bordered
              tableLayout="fixed"
              columns={[
                {
                  title: "Replica",
                  dataIndex: "replicaID",
                  width: 190,
                },
                {
                  title: "Issue",
                  dataIndex: "message",
                  ellipsis: true,
                },
              ]}
            />
          </div>
        }
      >
        <span>{children}</span>
      </Popover>
    );
  } else {
    return <>{children}</>;
  }
};
