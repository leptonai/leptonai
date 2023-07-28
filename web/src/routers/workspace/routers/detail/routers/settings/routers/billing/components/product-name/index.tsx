import { Tag } from "antd";
import { FC, useMemo } from "react";
import Stripe from "stripe";

export const ProductName: FC<{
  products: Stripe.Product[];
  priceId?: string;
}> = ({ products, priceId }) => {
  const product = useMemo(() => {
    return products.find(
      (i) => (i.default_price as Stripe.Price).id === priceId
    );
  }, [products, priceId]);
  return <Tag>{product?.name}</Tag>;
};
