import { css } from "@emotion/react";
import { PriceSummary } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/price-summary";
import { ProductName } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/product-name";
import { ProductQuantity } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/product-quantity";
import { ProductUnitPrice } from "@lepton-dashboard/routers/workspace/routers/detail/routers/settings/routers/billing/components/product-unit-price";
import { Table, Tag } from "antd";
import Decimal from "decimal.js";
import { FC, useMemo } from "react";
import Stripe from "stripe";

export const InvoiceTable: FC<{
  invoice: Stripe.UpcomingInvoice;
  products: Stripe.Product[];
}> = ({ invoice, products }) => {
  const dataSource = useMemo(() => {
    if (invoice.lines.data.every((e) => e.amount === 0)) {
      return invoice.lines.data;
    } else {
      return invoice.lines.data.filter((e) => e.amount > 0);
    }
  }, [invoice]);
  return (
    <Table
      scroll={{ x: "100%" }}
      css={css`
        .ant-table-summary {
          .ant-table-cell {
            border-bottom: none;
          }
        }
      `}
      dataSource={dataSource}
      rowKey="id"
      size="small"
      pagination={false}
      bordered={false}
      summary={() => (
        <Table.Summary fixed>
          <Table.Summary.Row>
            <Table.Summary.Cell index={0} colSpan={4} align="right">
              <PriceSummary name="Subtotal" amount={invoice.subtotal} />
              {invoice.total_discount_amounts?.[0].amount ? (
                <PriceSummary
                  name="Credits"
                  prefix="-"
                  amount={invoice.total_discount_amounts?.[0].amount}
                />
              ) : null}
              <PriceSummary name="Total" amount={invoice.total} />
              <PriceSummary name="Amount due" amount={invoice.amount_due} />
            </Table.Summary.Cell>
          </Table.Summary.Row>
        </Table.Summary>
      )}
      columns={[
        {
          title: "RESOURCE TYPE",
          dataIndex: "description",
          render: (_, data) => {
            return <ProductName products={products} priceId={data.price?.id} />;
          },
        },
        {
          title: "QUANTITY",
          dataIndex: "quantity",
          render: (q, data) => (
            <ProductQuantity
              quantity={q}
              products={products}
              priceId={data.price?.id}
            />
          ),
        },
        {
          title: "PRICE",
          dataIndex: "quantity",
          render: (_, data) => {
            return (
              <ProductUnitPrice products={products} priceId={data.price?.id} />
            );
          },
        },
        {
          title: "AMOUNT",
          dataIndex: "amount",
          render: (amount) => (
            <Tag bordered={false}>
              $ {new Decimal(amount).div(100).toFixed()}
            </Tag>
          ),
        },
      ]}
    />
  );
};
