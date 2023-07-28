import { Wallet } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Card } from "@lepton-dashboard/components/card";
import { Invoice } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/invoice";
import { Portal } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/portal";
import { Status } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/status";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { Space } from "antd";

import { FC } from "react";

export const Billing: FC = () => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const isBillingSupported =
    workspaceTrackerService.workspace?.isBillingSupported;

  return (
    <Card
      icon={<CarbonIcon icon={<Wallet />} />}
      borderless
      extra={isBillingSupported ? <Portal /> : null}
      shadowless
      title={
        <Space>
          Billing <Status />
        </Space>
      }
    >
      {isBillingSupported ? (
        <Invoice />
      ) : (
        <>The current workspace does not support billing yet</>
      )}
    </Card>
  );
};
