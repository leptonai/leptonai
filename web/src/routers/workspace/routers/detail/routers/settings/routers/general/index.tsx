import { CopyFile, Settings } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Card } from "@lepton-dashboard/components/card";

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
        bordered
        size="small"
        column={1}
        labelStyle={{ fontWeight: 500, color: theme.colorTextHeading }}
      >
        <Descriptions.Item label="Name">
          <Typography.Text
            copyable={{ icon: <CarbonIcon icon={<CopyFile />} /> }}
          >
            {workspaceTrackerService.workspace?.data.cluster_name}
          </Typography.Text>
        </Descriptions.Item>
        <Descriptions.Item label="Release date">
          <Typography.Text
            copyable={{ icon: <CarbonIcon icon={<CopyFile />} /> }}
          >
            {workspaceTrackerService.workspace?.data.build_time}
          </Typography.Text>
        </Descriptions.Item>
        <Descriptions.Item label="Version hash">
          <Typography.Text
            copyable={{ icon: <CarbonIcon icon={<CopyFile />} /> }}
          >
            {workspaceTrackerService.workspace?.data.git_commit}
          </Typography.Text>
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
};
