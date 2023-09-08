import { DocumentDownload, Launch } from "@carbon/icons-react";
import { css } from "@emotion/react";
import { DateParser } from "@lepton-dashboard/components/date-parser";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { InvoiceTable } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/invoice-table";
import {
  Button,
  Col,
  Collapse,
  Divider,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import dayjs from "dayjs";
import Decimal from "decimal.js";
import { ItemType } from "rc-collapse/es/interface";
import { FC, useMemo } from "react";
import Stripe from "stripe";

const Period: FC<{ start: number; end: number }> = ({ start, end }) => {
  return (
    <Tag>
      {dayjs(start * 1000).format("LL")} - {dayjs(end * 1000).format("LL")}
    </Tag>
  );
};

const colorMap: { [key: string]: string } = {
  paid: "success",
  draft: "default",
  open: "processing",
  void: "danger",
  uncollectible: "error",
};

export const Invoice: FC<{
  upcoming?: Stripe.UpcomingInvoice;
  open?: Stripe.Invoice;
  list: Stripe.Invoice[];
  products: Stripe.Product[];
}> = ({ upcoming, open, list, products }) => {
  const items: ItemType[] = useMemo(() => {
    const upcomingItem = upcoming && {
      key: "upcoming",
      label: <Typography.Text strong>Upcoming invoice</Typography.Text>,
      extra: (
        <Col xs={0} sm={0} md={24}>
          <Period start={upcoming.period_start} end={upcoming.period_end} />
        </Col>
      ),
      children: <InvoiceTable invoice={upcoming} products={products} />,
    };
    const openItem = open && {
      key: "open",
      label: <Typography.Text strong>Open invoice</Typography.Text>,
      extra: (
        <Space size={0} split={<Divider type="vertical" />}>
          <Button
            icon={<CarbonIcon icon={<Launch />} />}
            size="small"
            href={open.hosted_invoice_url!}
            onClick={(e) => e.stopPropagation()}
            target="_blank"
          >
            Make payment
          </Button>
          <Button
            icon={<CarbonIcon icon={<DocumentDownload />} />}
            onClick={(e) => e.stopPropagation()}
            size="small"
            href={open.invoice_pdf!}
            target="_blank"
          >
            Download
          </Button>
          <Col xs={0} sm={0} md={24}>
            <Period start={open.period_start} end={open.period_end} />
          </Col>
        </Space>
      ),
      children: <InvoiceTable invoice={open} products={products} />,
    };
    const invoiceList = {
      key: "list",
      label: <Typography.Text strong>Invoices</Typography.Text>,
      children: (
        <Table
          scroll={{ x: "100%" }}
          size="small"
          bordered={false}
          columns={[
            {
              dataIndex: "status",
              title: "STATUS",
              render: (status) => (
                <Tag bordered={false} color={colorMap[status]}>
                  {status.toUpperCase()}
                </Tag>
              ),
            },
            {
              dataIndex: "created",
              title: "DATE",
              render: (_, record: Stripe.Invoice) => (
                <>
                  <DateParser detail date={record.created * 1000} />
                </>
              ),
            },
            {
              dataIndex: "total",
              title: "AMOUNT",
              render: (total) => (
                <Tag bordered={false}>
                  ${new Decimal(total).dividedBy(100).toFixed()}
                </Tag>
              ),
            },
            {
              dataIndex: "id",
              align: "right",
              title: (
                <div
                  css={css`
                    margin-right: 8px;
                  `}
                >
                  ACTIONS
                </div>
              ),
              render: (_, record) => (
                <Space size={0} split={<Divider type="vertical" />}>
                  {record.hosted_invoice_url && (
                    <Button
                      icon={<CarbonIcon icon={<Launch />} />}
                      type="text"
                      size="small"
                      href={record.hosted_invoice_url}
                      target="_blank"
                    >
                      Detail
                    </Button>
                  )}
                  {record.invoice_pdf && (
                    <Button
                      icon={<CarbonIcon icon={<DocumentDownload />} />}
                      type="text"
                      size="small"
                      href={record.invoice_pdf}
                      target="_blank"
                    >
                      Download
                    </Button>
                  )}
                </Space>
              ),
            },
          ]}
          rowKey="id"
          dataSource={list.filter((e) => e.subtotal > 0)}
          pagination={false}
        />
      ),
    };
    return [openItem, upcomingItem, invoiceList].filter(Boolean) as ItemType[];
  }, [upcoming, open, products, list]);
  return (
    <Collapse
      size="small"
      css={css`
        background: transparent;
        .ant-collapse-content {
          overflow: hidden;
        }
        .ant-collapse-content-box {
          padding: 0 !important;
        }
      `}
      defaultActiveKey={[open ? "open" : "upcoming"]}
      items={items}
    />
  );
};
