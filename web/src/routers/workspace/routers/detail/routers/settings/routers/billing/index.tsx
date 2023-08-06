import { Wallet } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Card } from "@lepton-dashboard/components/card";
import { MinThemeProvider } from "@lepton-dashboard/components/min-theme-provider";
import { Credit } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/credit";
import { Invoice } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/invoice";
import { Portal } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/portal";
import { Status } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/status";
import { BillingService } from "@lepton-dashboard/routers/workspace/services/billing.service";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Col, Row, Space } from "antd";

import { FC, useState } from "react";

export const Billing: FC = () => {
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const isBillingSupported =
    workspaceTrackerService.workspace?.isBillingSupported;
  const [invoiceLoading, setInvoiceLoading] = useState(true);
  const billingService = useInject(BillingService);

  const { upcoming, open, list, products } = useStateFromObservable(
    () => billingService.getInvoice(),
    { products: [], list: [] },
    {
      next: () => {
        setInvoiceLoading(false);
      },
    }
  );

  const creditInvoice = open || upcoming;

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
        <MinThemeProvider>
          <Card borderless shadowless paddingless loading={invoiceLoading}>
            {list && (
              <Row gutter={[0, 16]}>
                <Col span={24}>
                  {creditInvoice && <Credit invoice={creditInvoice} />}
                </Col>
                <Col span={24}>
                  <Invoice
                    list={list}
                    open={open}
                    upcoming={upcoming}
                    products={products}
                  />
                </Col>
              </Row>
            )}
          </Card>
        </MinThemeProvider>
      ) : (
        <>The current workspace does not support billing yet</>
      )}
    </Card>
  );
};
