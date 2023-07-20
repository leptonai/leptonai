import { Wallet } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Card } from "@lepton-dashboard/components/card";
import { Invoice } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/invoice";
import { Portal } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/portal";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";

import { FC } from "react";

export const Billing: FC = () => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const supportBilling = !!workspaceTrackerService.workspace?.auth.status;

  return (
    <Card
      icon={<CarbonIcon icon={<Wallet />} />}
      borderless
      extra={<Portal />}
      shadowless
      title="Billing"
    >
      {supportBilling ? (
        <Invoice />
      ) : (
        <>The current workspace does not support billing yet</>
      )}
    </Card>
  );
};
