import { css } from "@emotion/react";
import { Card } from "@lepton-dashboard/components/card";
import { Col, Progress, Row, Typography } from "antd";
import dayjs from "dayjs";
import Decimal from "decimal.js";
import { FC, useMemo } from "react";
import Stripe from "stripe";

export const Credit: FC<{ invoice: Stripe.UpcomingInvoice }> = ({
  invoice,
}) => {
  const creditGranted = invoice.discount?.coupon.amount_off;
  const creditReason = invoice.discount?.coupon.name;
  const creditUsed = invoice.total_discount_amounts?.[0].amount;
  const creditExpired = (invoice.period_end || 0) * 1000;
  const percentage = useMemo(() => {
    if (!creditGranted || creditUsed === undefined) {
      return null;
    } else {
      return new Decimal(creditUsed).mul(100).div(creditGranted).toNumber();
    }
  }, [creditUsed, creditGranted]);

  if (creditGranted && creditUsed !== undefined && percentage !== null) {
    return (
      <Card
        css={css`
          max-width: 400px;
        `}
      >
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
              Expired at {dayjs(creditExpired).format("LL")}
            </Typography.Text>
          </Col>
        </Row>
        <Progress
          css={css`
            margin: 4px 0 0 0;
            .ant-progress-inner,
            .ant-progress-bg {
              border-radius: 2px !important;
            }
          `}
          showInfo={false}
          size={["100%", 8]}
          percent={percentage}
          status="normal"
        />
      </Card>
    );
  } else {
    return <></>;
  }
};
