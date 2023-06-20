import { CopyFile, View, ViewOff } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Card } from "@lepton-dashboard/routers/workspace/components/card";
import { WorkspaceTrackerService } from "@lepton-dashboard/routers/workspace/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { Button, Divider, Space, Table, Typography } from "antd";
import { ColumnsType } from "antd/es/table";
import { FC, useMemo, useState } from "react";

export const ApiTokens: FC = () => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const data = [{ token: workspaceTrackerService.cluster!.auth.token }];
  const [mask, setMask] = useState(true);
  const columns: ColumnsType<{ token: string }> = useMemo(
    () => [
      {
        title: "Token",
        dataIndex: "token",
        render: (v) => (mask ? "******" : v),
      },
      {
        title: "Actions",
        dataIndex: "token",
        render: (v) => {
          return (
            <Space size={0} split={<Divider type="vertical" />}>
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
              />
              <Button
                size="small"
                type="text"
                icon={
                  <Typography.Text
                    copyable={{
                      icon: <CarbonIcon icon={<CopyFile />} />,
                      text: v,
                    }}
                  />
                }
              />
            </Space>
          );
        },
      },
    ],
    [mask]
  );
  return (
    <Card borderless shadowless title="API Tokens">
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
