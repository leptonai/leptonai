import { stripeClient } from "@/utils/stripe/stripe-client";
import { retrieveSubscriptionItem } from "@/utils/stripe/retrieve-subscription-item";
import { supabaseAdminClient } from "@/utils/supabase";
import type { NextApiRequest, NextApiResponse } from "next";

// Report storage usage to stripe
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
    const id = body.record.id;
    const workspaceId = body.record.workspace_id;
    const usage = body.record.size_gb;
    const timestamp = Math.round(
      new Date(body.record.end_time).getTime() / 1000,
    );

    const subscriptionItem = await retrieveSubscriptionItem(
      workspaceId,
      "storage",
    );

    if (!subscriptionItem) {
      return res.status(412).send("No subscription shape matched");
    }

    const usageRecord = await stripeClient.subscriptionItems.createUsageRecord(
      subscriptionItem.id,
      { quantity: usage, timestamp },
      {
        idempotencyKey: id,
      },
    );

    await supabaseAdminClient
      .from("storage_hourly")
      .update({ stripe_usage_record_id: usageRecord.id })
      .eq("id", id);

    res.status(200).json(usageRecord);
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.status(500).send(`Error: ${errorMessage}`);
  }
}