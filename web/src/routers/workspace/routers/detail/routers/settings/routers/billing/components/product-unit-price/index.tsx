import { Tag } from "antd";
import Decimal from "decimal.js";
import { FC, useMemo } from "react";
import Stripe from "stripe";

export const ProductUnitPrice: FC<{
  products: Stripe.Product[];
  priceId?: string;
}> = ({ products, priceId }) => {
  const product = products.find(
    (i) => (i.default_price as Stripe.Price).id === priceId
  );
  const unit = useMemo(() => {
    const unit_price = (product?.default_price as Stripe.Price).tiers?.[0]
      .unit_amount_decimal;
    return unit_price !== undefined &&
      unit_price !== null &&
      typeof +unit_price === "number"
      ? new Decimal(+unit_price).dividedBy(100).toFixed()
      : "-";
  }, [product]);

  return (
    <Tag bordered={false}>
      ${unit} {product?.name === "storage" ? "/ GB / hour" : "/ minutes"}
    </Tag>
  );
};
