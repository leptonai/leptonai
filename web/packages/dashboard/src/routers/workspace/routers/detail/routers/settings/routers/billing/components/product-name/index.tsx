import { DateParser } from "@lepton-dashboard/components/date-parser";
import { Tag } from "antd";
import { FC, useMemo } from "react";
import Stripe from "stripe";

export const ProductName: FC<{
  products: Stripe.Product[];
  item: Stripe.InvoiceLineItem;
}> = ({ products, item }) => {
  const product = useMemo(() => {
    return products.find(
      (i) => (i.default_price as Stripe.Price).id === item.price?.id
    );
  }, [products, item]);
  if (product?.name === "Standard Plan") {
    return (
      <>
        {item.description}{" "}
        <Tag>
          <DateParser format="MMM D" date={item.period.start * 1000} /> -{" "}
          <DateParser format="MMM D" date={item.period.end * 1000} />
        </Tag>
      </>
    );
  }
  return <>{product?.name}</>;
};
