import { Settings } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { MinThemeProvider } from "@lepton-dashboard/components/min-theme-provider";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Card } from "@lepton-dashboard/components/card";
import { Quotas } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/general/quotas";
import { WorkspaceService } from "@lepton-dashboard/routers/workspace/services/workspace.service";

import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Descriptions, Typography } from "antd";
import { FC, useState } from "react";

export const General: FC = () => {
  const [loading, setLoading] = useState(true);
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const workspaceService = useInject(WorkspaceService);
  const workspaceDetail = useStateFromObservable(
    () => workspaceService.getWorkspaceDetail(),
    null,
    { next: () => setLoading(false), error: () => setLoading(false) }
  );
  const theme = useAntdTheme();
  return (
    <Card
      loading={loading}
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

        {workspaceDetail && (
          <>
            <Descriptions.Item label="Version">
              <Typography.Text>{workspaceDetail?.git_commit}</Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="Date">
              <Typography.Text>{workspaceDetail?.build_time}</Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="Resource">
              <MinThemeProvider>
                <Quotas workspaceDetail={workspaceDetail} />
              </MinThemeProvider>
            </Descriptions.Item>
          </>
        )}
      </Descriptions>
    </Card>
  );
};
