import { getStripeClient } from "@/utils/stripe/stripe-client";
import Stripe from "stripe";

export const retrieveSubscriptionItem = async (
  shape: string,
  chargeable: boolean,
  subscription_id: string | null
): Promise<Stripe.SubscriptionItem | null> => {
  if (subscription_id) {
    const stripeClient = getStripeClient(chargeable);
    const subscription = await stripeClient.subscriptions.retrieve(
      subscription_id
    );
    return (
      subscription.items.data.find((i) => i.metadata.shape === shape) || null
    );
  }
  return null;
};
