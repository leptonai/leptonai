import { stripeClient } from "@/utils/stripe";
import { supabase } from "@/utils/supabase";
import type { NextApiRequest, NextApiResponse } from "next";

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
      items: [
        {
          price: "price_1NVbn2BcUfXYxWWViU0XrNgA",
          metadata: { shape: "cpu.small" },
        },
        {
          price: "price_1NVbnlBcUfXYxWWVpXUeFNnl",
          metadata: { shape: "cpu.medium" },
        },
        {
          price: "price_1NVboUBcUfXYxWWVLB9kZXzA",
          metadata: { shape: "cpu.large" },
        },
        {
          price: "price_1NVbpbBcUfXYxWWVTfS6a74e",
          metadata: { shape: "gpu.t4" },
        },
        {
          price: "price_1NVbqXBcUfXYxWWVVQRL3Gl3",
          metadata: { shape: "gpu.a10" },
        },
        {
          price: "price_1NVbrIBcUfXYxWWVk7G25XEB",
          metadata: { shape: "gpu.a100" },
        },
      ],
      coupon: "NolzLBLL",
    });

    const updated = {
      consumer_id: consumer.id,
      subscription_id: subscription.id,
    };

    await supabase
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
