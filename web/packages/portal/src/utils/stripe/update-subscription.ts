import { getAvailableProducts } from "@/utils/stripe/available-products";
import { getStripeClient } from "@/utils/stripe/stripe-client";
import { Database } from "@lepton/database";
import Stripe from "stripe";

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
  chargeable: boolean,
  tier: Database["public"]["Enums"]["tier"] | null
) {
  const stripeClient = getStripeClient(chargeable);
  const subscription = await stripeClient.subscriptions.retrieve(
    subscriptionId
  );
  const previousItems = subscription.items.data || [];

  const addedItems = getAvailableProducts(chargeable, tier).filter(
    (p) => !previousItems.find((i) => i.price.id === p.price)
  );

  const deletedItems: Stripe.SubscriptionCreateParams.Item[] = previousItems
    .filter(
      (p) =>
        !getAvailableProducts(chargeable, tier).find(
          (i) => i.price === p.price.id
        )
    )
    .map((p) => {
      return {
        deleted: true,
        id: p.id,
        metadata: p.metadata,
      };
    });

  await stripeClient.subscriptions.update(subscriptionId, {
    items: [...addedItems, ...deletedItems],
  });
}
