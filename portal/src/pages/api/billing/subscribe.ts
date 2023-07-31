import { AvailableProducts } from "@/utils/stripe/available-products";
import { stripeClient } from "@/utils/stripe/stripe-client";
import { supabaseAdminClient } from "@/utils/supabase";
import type { NextApiRequest, NextApiResponse } from "next";

// Subscribe a workspace to a plan
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  if (
    req.method !== "POST" ||
    req.query.LEPTON_API_SECRET !== process.env.LEPTON_API_SECRET
  ) {
    return res.status(401).send("You are not authorized to call this API");
  }

  try {
    const body = req.body;

    const workspace_id = body.record.id;

    const consumer = await stripeClient.customers.create({
      metadata: {
        workspace_id,
      },
    });

    const subscription = await stripeClient.subscriptions.create({
      customer: consumer.id,
      metadata: {
        workspace_id,
      },
      billing_thresholds: {
        amount_gte: 50,
        reset_billing_cycle_anchor: false,
      },
      items: AvailableProducts,
      coupon: "NolzLBLL",
    });

    const updated = {
      consumer_id: consumer.id,
      subscription_id: subscription.id,
    };

    await supabaseAdminClient
      .from("workspaces")
      .update({ consumer_id: consumer.id, subscription_id: subscription.id })
      .eq("id", workspace_id);

    res.status(200).json(updated);
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.status(500).send(`Error: ${errorMessage}`);
  }
}
