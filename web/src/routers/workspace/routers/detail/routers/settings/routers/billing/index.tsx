import { Wallet } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Card } from "@lepton-dashboard/components/card";
import { MinThemeProvider } from "@lepton-dashboard/components/min-theme-provider";
import { Credit } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/credit";
import { Invoice } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/invoice";
import { Payment } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/payment";
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
  const paymentMethodAttached =
    !!workspaceTrackerService.workspace?.auth.paymentMethodAttached;
  const [invoiceLoading, setInvoiceLoading] = useState(true);
  const billingService = useInject(BillingService);

  const { upcoming, open, list, products, coupon, current_period } =
    useStateFromObservable(
      () => billingService.getInvoice(),
      {
        products: [],
        list: [],
        coupon: null,
        current_period: { start: 0, end: 0 },
      },
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
                  <Row gutter={[16, 16]}>
                    {coupon && creditInvoice && (
                      <Col flex="1 0 400px">
                        <Credit
                          coupon={coupon}
                          current_period={current_period}
                          invoice={creditInvoice}
                        />
                      </Col>
                    )}
                    <Col flex="1 0 300px">
                      <Payment paymentMethodAttached={paymentMethodAttached} />
                    </Col>
                  </Row>
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
