import { getAvailableCoupons } from "@/utils/stripe/available-coupons";
import { createConsumer } from "@/utils/stripe/create-consumer";
import { createSubscription } from "@/utils/stripe/create-subscription";
import { supabaseAdminClient } from "@/utils/supabase";
import { Database } from "@lepton/database";

export const setupWorkspaceSubscription = async (
  workspaceId: string,
  chargeable: boolean
) => {
  const coupon = getAvailableCoupons("10", chargeable);

  const consumer = await createConsumer(workspaceId, coupon, chargeable);

  const subscription = await createSubscription(
    consumer.id,
    workspaceId,
    chargeable
  );

  const updated: Database["public"]["Tables"]["workspaces"]["Update"] = {
    consumer_id: consumer.id,
    subscription_id: subscription.id,
    coupon_id: coupon,
    chargeable: chargeable,
  };

  await supabaseAdminClient
    .from("workspaces")
    .update(updated)
    .eq("id", workspaceId);

  return updated;
};
