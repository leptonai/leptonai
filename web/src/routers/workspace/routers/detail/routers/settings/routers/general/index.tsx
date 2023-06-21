import { Settings } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Card } from "@lepton-dashboard/routers/workspace/components/card";

import { WorkspaceTrackerService } from "@lepton-dashboard/routers/workspace/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { Descriptions } from "antd";
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
        bordered
        size="small"
        column={1}
        labelStyle={{ fontWeight: 500, color: theme.colorTextHeading }}
      >
        <Descriptions.Item label="Name">
          {workspaceTrackerService.cluster?.data.cluster_name}
        </Descriptions.Item>
        <Descriptions.Item label="Release date">
          {workspaceTrackerService.cluster?.data.build_time}
        </Descriptions.Item>
        <Descriptions.Item label="Version hash">
          {workspaceTrackerService.cluster?.data.git_commit}
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
};
