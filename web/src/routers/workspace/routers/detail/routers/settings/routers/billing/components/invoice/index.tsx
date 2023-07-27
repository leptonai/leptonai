import { css } from "@emotion/react";
import { Card } from "@lepton-dashboard/components/card";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { InvoiceTable } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/invoice-table";
import { BillingService } from "@lepton-dashboard/routers/workspace/services/billing.service";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { Collapse, Descriptions, Progress, Typography } from "antd";
import dayjs from "dayjs";
import Decimal from "decimal.js";
import { FC, useMemo, useState } from "react";

export const Invoice: FC = () => {
  const [invoiceLoading, setInvoiceLoading] = useState(true);
  const billingService = useInject(BillingService);
  const { upcoming, open, products } = useStateFromObservable(
    () => billingService.getInvoice(),
    { products: [] },
    {
      next: () => {
        setInvoiceLoading(false);
      },
    }
  );
  const invoice = useMemo(() => {
    if (open) {
      return {
        name: "Invoice",
        data: open,
      };
    }
    if (upcoming) {
      return {
        name: "Upcoming invoice",
        data: upcoming,
      };
    } else {
      return null;
    }
  }, [upcoming, open]);
  const creditGranted = invoice?.data?.discount?.coupon.amount_off;
  const creditUsed = invoice?.data?.total_discount_amounts?.[0].amount;
  const creditExpired = (invoice?.data?.period_end || 0) * 1000;
  const theme = useAntdTheme();
  const percentage = useMemo(() => {
    if (!creditGranted || creditUsed === undefined) {
      return null;
    } else {
      return new Decimal(creditUsed).mul(100).div(creditGranted).toNumber();
    }
  }, [creditUsed, creditGranted]);
  return (
    <Card borderless shadowless paddingless loading={invoiceLoading}>
      {invoice && (
        <Collapse
          size="small"
          css={css`
            .ant-collapse-content {
              overflow: hidden;
            }
            .ant-collapse-content-box {
              padding: 0 !important;
            }
          `}
          defaultActiveKey={["credits"]}
          items={[
            {
              key: "credits",
              label: <Typography.Text strong>Credits</Typography.Text>,
              children:
                creditGranted &&
                creditUsed !== undefined &&
                percentage !== null ? (
                  <Descriptions
                    css={css`
                      .ant-descriptions-view {
                        border: none !important;
                      }
                      .ant-descriptions-item-label {
                        font-weight: 600;
                        color: ${theme.colorTextHeading} !important;
                      }
                    `}
                    bordered
                    layout="vertical"
                    column={{ xxl: 3, xl: 3, lg: 3, md: 3, sm: 2, xs: 1 }}
                    size="small"
                  >
                    <Descriptions.Item label="CREDIT GRANTED">
                      ${new Decimal(creditGranted).div(100).toFixed()}
                    </Descriptions.Item>
                    <Descriptions.Item label="EXPIRES">
                      {dayjs(creditExpired).format("LL")}
                    </Descriptions.Item>
                    <Descriptions.Item label="CREDIT USED">
                      <Progress
                        css={css`
                          margin: 0;
                          .ant-progress-text {
                            width: auto;
                          }
                        `}
                        format={() => (
                          <>
                            ${new Decimal(creditUsed).div(100).toFixed()} / $
                            {new Decimal(creditGranted).div(100).toFixed()}
                          </>
                        )}
                        size={[200, 8]}
                        percent={percentage}
                        status="normal"
                      />
                    </Descriptions.Item>
                  </Descriptions>
                ) : (
                  <Typography.Paragraph>No credit granted</Typography.Paragraph>
                ),
            },
            {
              key: "invoice",
              label: <Typography.Text strong>{invoice.name}</Typography.Text>,
              extra: (
                <>
                  {dayjs(invoice.data.period_start * 1000).format("LL")} -{" "}
                  {dayjs(invoice.data.period_end * 1000).format("LL")}
                </>
              ),
              children: (
                <InvoiceTable invoice={invoice.data} products={products} />
              ),
            },
          ]}
        />
      )}
    </Card>
  );
};
