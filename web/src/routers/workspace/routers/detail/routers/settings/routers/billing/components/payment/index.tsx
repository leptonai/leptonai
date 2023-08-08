import { css } from "@emotion/react";
import { Card } from "@lepton-dashboard/components/card";
import { Portal } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/portal";
import { Col, Row, Typography } from "antd";
import Decimal from "decimal.js";
import { FC } from "react";
import Stripe from "stripe";

export const Payment: FC<{
  paymentMethodAttached: boolean;
  invoice?: Stripe.UpcomingInvoice;
}> = ({ paymentMethodAttached, invoice }) => {
  return (
    <Card>
      <Row justify="space-between" gutter={[16, 16]} wrap={false}>
        <Col flex={1}>
          <Typography.Title
            level={4}
            css={css`
              margin-top: 0;
              margin-bottom: 4px !important;
            `}
          >
            NEXT PAYMENT
          </Typography.Title>
          <Typography.Paragraph type="secondary">
            Change how you pay
          </Typography.Paragraph>
          <Portal paymentMethodAttached={paymentMethodAttached} />
        </Col>
        {invoice && (
          <Col flex={0}>
            <Typography.Title
              level={2}
              css={css`
                margin-top: 0;
                white-space: nowrap;
                margin-bottom: 4px !important;
              `}
            >
              ${new Decimal(invoice.amount_due).dividedBy(100).toFixed()}
            </Typography.Title>
          </Col>
        )}
      </Row>
    </Card>
  );
};
