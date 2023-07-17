import { stripeClient } from "@/utils/stripe";
import { supabase } from "@/utils/supabase";
import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  if (
    req.method !== "POST" ||
    req.query.API_ROUTE_SECRET !== process.env.API_ROUTE_SECRET
  ) {
    return res.status(401).send("You are not authorized to call this API");
  }

  const body = req.body;
  const id = body.record.id;
  const workspaceId = body.record.workspace_id;
  const shape = body.record.shape;
  const usage = body.record.usage;
  const timestamp = Math.round(
    new Date(body.record.start_time).getTime() / 1000,
  );

  const { data: subscriptionId } = await supabase
    .from("workspaces")
    .select("subscription_id")
    .eq("id", workspaceId);

  if (!subscriptionId || subscriptionId.length === 0) {
    return res.status(412).send("Workspace has no subscription");
  }

  const subscription = await stripeClient.subscriptions.retrieve(
    subscriptionId[0].subscription_id,
  );

  const subscriptionItem = subscription.items.data.find(
    (i) => i.metadata.shape === shape,
  );

  if (!subscriptionItem) {
    return res.status(412).send("No subscription shape matched");
  }

  const usageRecord = await stripeClient.subscriptionItems.createUsageRecord(
    subscriptionItem.id,
    { quantity: usage, timestamp },
  );

  await supabase
    .from("hourly_metering")
    .update({ stripe_usage_record_id: usageRecord.id })
    .eq("id", id);

  res.status(200).json(usageRecord);
}
