import { getAvailableProducts } from "@/utils/stripe/available-products";
import { getStripeClient } from "@/utils/stripe/stripe-client";

export async function updateCustomerAmountGTE(
  customer: string,
  amountGTE: number,
  chargeable: boolean
) {
  const stripeClient = getStripeClient(chargeable);
  const { data: subscriptions } = await stripeClient.subscriptions.list({
    customer,
  });
  await Promise.all(
    subscriptions.map(async ({ id }) => {
      await stripeClient.subscriptions.update(id, {
        billing_thresholds: {
          amount_gte: amountGTE,
          reset_billing_cycle_anchor: false,
        },
      });
    })
  );
  return subscriptions.map(({ id }) => id);
}

export async function updateSubscriptionItems(
  subscriptionId: string,
  chargeable: boolean
) {
  const stripeClient = getStripeClient(chargeable);
  const subscription = await stripeClient.subscriptions.retrieve(
    subscriptionId
  );
  const previousItems = subscription.items.data || [];

  const updatedItems = getAvailableProducts(chargeable).filter(
    (p) => !previousItems.find((i) => i.price.id === p.price)
  );

  await stripeClient.subscriptions.update(subscriptionId, {
    items: updatedItems,
  });
}
