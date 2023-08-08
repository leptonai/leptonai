import { Settings } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { MinThemeProvider } from "@lepton-dashboard/components/min-theme-provider";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Card } from "@lepton-dashboard/components/card";
import { Quotas } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/components/quotas";

import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { Descriptions, Typography } from "antd";
import { FC } from "react";

export const General: FC = () => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const theme = useAntdTheme();
  return (
    <Card
      icon={<CarbonIcon icon={<Settings />} />}
      borderless
      shadowless
      title="General"
    >
      <Descriptions
        column={1}
        labelStyle={{
          fontWeight: 500,
          width: "120px",
          color: theme.colorTextHeading,
        }}
      >
        <Descriptions.Item label="ID">
          <Typography.Text>
            {workspaceTrackerService.workspace?.auth.id}
          </Typography.Text>
        </Descriptions.Item>
        {workspaceTrackerService.workspace?.auth.displayName && (
          <Descriptions.Item label="Name">
            <Typography.Text>
              {workspaceTrackerService.workspace?.auth.displayName}
            </Typography.Text>
          </Descriptions.Item>
        )}
        <Descriptions.Item label="Version">
          <Typography.Text>
            {workspaceTrackerService.workspace?.data?.git_commit}
          </Typography.Text>
        </Descriptions.Item>
        <Descriptions.Item label="Date">
          <Typography.Text>
            {workspaceTrackerService.workspace?.data?.build_time}
          </Typography.Text>
        </Descriptions.Item>
        <Descriptions.Item label="Resource">
          <MinThemeProvider>
            <Quotas />
          </MinThemeProvider>
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
};
