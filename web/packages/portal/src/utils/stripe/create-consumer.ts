import { getStripeClient } from "@/utils/stripe/stripe-client";

export const createConsumer = async (
  workspaceId: string,
  couponId: string,
  chargeable: boolean
) => {
  const stripeClient = getStripeClient(chargeable);

  return await stripeClient.customers.create({
    metadata: {
      workspace_id: workspaceId,
    },
    coupon: couponId,
  });
};
