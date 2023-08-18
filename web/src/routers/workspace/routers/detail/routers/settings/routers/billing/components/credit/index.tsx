import { css } from "@emotion/react";
import { Card } from "@lepton-dashboard/components/card";
import { Col, Progress, Row, Typography } from "antd";
import dayjs from "dayjs";
import Decimal from "decimal.js";
import { FC, useMemo } from "react";
import Stripe from "stripe";

export const Credit: FC<{
  invoice: Stripe.UpcomingInvoice;
  coupon: Stripe.Coupon;
  current_period: { start: number; end: number };
}> = ({ invoice, coupon, current_period }) => {
  const creditGranted = coupon.amount_off;
  const creditReason = coupon.name;
  // the credit is used up in previous invoice if no discount in current invoice
  const creditUsed = invoice.total_discount_amounts?.[0]
    ? invoice.total_discount_amounts?.[0]?.amount
    : coupon.amount_off;
  const creditExpired = current_period.end;
  const percentage = useMemo(() => {
    if (!creditGranted || creditUsed === undefined || creditUsed === null) {
      return null;
    } else {
      return new Decimal(creditUsed).mul(100).div(creditGranted).toNumber();
    }
  }, [creditUsed, creditGranted]);

  if (
    creditGranted &&
    creditUsed !== null &&
    creditUsed !== undefined &&
    percentage !== null
  ) {
    return (
      <Card>
        <Row justify="space-between">
          <Col flex={0}>
            <Typography.Title
              level={4}
              css={css`
                margin-top: 0;
                margin-bottom: 16px !important;
              `}
            >
              {creditReason}
            </Typography.Title>
          </Col>
        </Row>
        <Row justify="space-between">
          <Col flex={0}>
            <Typography.Text>
              ${new Decimal(creditUsed).div(100).toFixed()} of $
              {new Decimal(creditGranted).div(100).toFixed()} used
            </Typography.Text>
          </Col>
          <Col flex={0}>
            <Typography.Text type="secondary">
              Expires on {dayjs(creditExpired).format("LL")}
            </Typography.Text>
          </Col>
        </Row>
        <Progress
          css={css`
            margin: 4px 0 0 0;
            .ant-progress-inner,
            .ant-progress-bg {
              border-radius: 0 !important;
            }
          `}
          showInfo={false}
          size={["100%", 4]}
          percent={percentage}
          status="normal"
        />
      </Card>
    );
  } else {
    return <></>;
  }
};
