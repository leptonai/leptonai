import { Card } from "@lepton-dashboard/routers/workspace/components/card";

import { WorkspaceTrackerService } from "@lepton-dashboard/routers/workspace/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { Descriptions } from "antd";
import { FC } from "react";

export const General: FC = () => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  return (
    <Card borderless shadowless title="General">
      <Descriptions bordered size="small" column={1}>
        <Descriptions.Item label="Name">
          {workspaceTrackerService.cluster?.data.cluster_name}
        </Descriptions.Item>
        <Descriptions.Item label="Build Time">
          {workspaceTrackerService.cluster?.data.build_time}
        </Descriptions.Item>
        <Descriptions.Item label="Build Hash">
          {workspaceTrackerService.cluster?.data.git_commit}
        </Descriptions.Item>
      </Descriptions>
    </Card>
  );
};
