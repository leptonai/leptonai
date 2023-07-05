import { CopyFile, Password, View, ViewOff } from "@carbon/icons-react";
import { ActionsHeader } from "@lepton-dashboard/components/actions-header";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Card } from "../../../../../../../../components/card";
import { WorkspaceTrackerService } from "@lepton-dashboard/routers/workspace/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { Button, Table, Typography } from "antd";
import { ColumnsType } from "antd/es/table";
import { FC, useMemo, useState } from "react";

export const ApiTokens: FC = () => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const data = [{ token: workspaceTrackerService.workspace!.auth.token }];
  const [mask, setMask] = useState(true);
  const columns: ColumnsType<{ token: string }> = useMemo(
    () => [
      {
        title: "Token",
        dataIndex: "token",
        render: (v) => (
          <Typography.Text
            copyable={{
              icon: <CarbonIcon icon={<CopyFile />} />,
              text: v,
            }}
          >
            {mask ? "••••••••••••" : v}
          </Typography.Text>
        ),
      },
      {
        title: <ActionsHeader />,
        dataIndex: "token",
        render: () => (
          <Button
            size="small"
            type="text"
            icon={
              mask ? (
                <CarbonIcon icon={<View />} />
              ) : (
                <CarbonIcon icon={<ViewOff />} />
              )
            }
            onClick={() => {
              setMask(!mask);
            }}
          >
            {mask ? "View" : "Hide"}
          </Button>
        ),
      },
    ],
    [mask]
  );
  return (
    <Card
      icon={<CarbonIcon icon={<Password />} />}
      borderless
      shadowless
      title="API Tokens"
    >
      <Table
        size="small"
        pagination={false}
        tableLayout="fixed"
        bordered
        dataSource={data}
        rowKey="token"
        columns={columns}
      />
    </Card>
  );
};
