import { FC, useMemo } from "react";
import Stripe from "stripe";

export const ProductQuantity: FC<{
  products: Stripe.Product[];
  quantity: string;
  priceId?: string;
}> = ({ products, priceId, quantity }) => {
  const product = useMemo(() => {
    return products.find(
      (i) => (i.default_price as Stripe.Price).id === priceId
    );
  }, [products, priceId]);

  return (
    <>
      {quantity} {product?.name === "storage" ? "GB * hour" : "minutes"}
    </>
  );
};
