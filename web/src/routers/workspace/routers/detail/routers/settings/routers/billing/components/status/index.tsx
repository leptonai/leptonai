import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { Tag } from "antd";
import { FC } from "react";

export const Status: FC = () => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const isBillingSupported =
    workspaceTrackerService.workspace?.isBillingSupported;
  const status = workspaceTrackerService.workspace?.auth.status;
  if (isBillingSupported) {
    if (status === "active") {
      return (
        <Tag bordered={false} color="success">
          ACTIVE
        </Tag>
      );
    } else if (status === "past_due") {
      return (
        <Tag bordered={false} color="past_due">
          PAST DUE
        </Tag>
      );
    }
  }
  return <></>;
};
