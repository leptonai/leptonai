import { AvailableProducts } from "@/utils/stripe/available-products";
import { stripeClient } from "@/utils/stripe/stripe-client";

export async function updateCustomerAmountGTE(
  customer: string,
  amountGTE: number,
) {
  const { data: subscriptions } = await stripeClient.subscriptions.list({
    customer,
  });
  await Promise.all(
    subscriptions
      .filter(({ status }) => status === "active")
      .map(async ({ id }) => {
        await stripeClient.subscriptions.update(id, {
          billing_thresholds: {
            amount_gte: amountGTE,
            reset_billing_cycle_anchor: false,
          },
        });
      }),
  );
  return subscriptions.map(({ id }) => id);
}

export async function updateSubscriptionItems(subscriptionId: string) {
  const subscription = await stripeClient.subscriptions.retrieve(
    subscriptionId,
  );
  const previousItems = subscription.items.data || [];

  const updatedItems = AvailableProducts.filter(
    (p) => !previousItems.find((i) => i.price.id === p.price),
  );

  await stripeClient.subscriptions.update(subscriptionId, {
    items: updatedItems,
  });
}
