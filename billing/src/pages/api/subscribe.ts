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

  const consumer = await stripeClient.customers.create({
    name: body.record.id,
  });

  const subscription = await stripeClient.subscriptions.create({
    customer: consumer.id,
    items: [
      {
        price: "price_1NTKPTBcUfXYxWWVOfMFn9DA",
        metadata: { shape: "gpu.a10" },
      },
      {
        price: "price_1NTKOIBcUfXYxWWVJnXsjccc",
        metadata: { shape: "gpu.t4" },
      },
      {
        price: "price_1NTKNHBcUfXYxWWVVmx8QMSI",
        metadata: { shape: "cpu.large" },
      },
      {
        price: "price_1NSdc4BcUfXYxWWVmuu2ODKM",
        metadata: { shape: "cpu.medium" },
      },
      {
        price: "price_1NSdayBcUfXYxWWVGEjTuBEF",
        metadata: { shape: "cpu.small" },
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
    .eq("id", body.record.id);

  res.status(200).json(updated);
}
