import { stripeClient } from "@/utils/stripe/stripe-client";
import { supabaseAdminClient } from "@/utils/supabase";
import Stripe from "stripe";

export const retrieveSubscriptionItem = async (
  workspaceId: string,
  shape: string
): Promise<Stripe.SubscriptionItem | null> => {
  const { data: subscriptionId } = await supabaseAdminClient
    .from("workspaces")
    .select("subscription_id")
    .not("subscription_id", "is", null)
    .eq("id", workspaceId);

  if (subscriptionId && subscriptionId.length > 0) {
    const subscription = await stripeClient.subscriptions.retrieve(
      subscriptionId[0].subscription_id!
    );

    return (
      subscription.items.data.find((i) => i.metadata.shape === shape) || null
    );
  }
  return null;
};
