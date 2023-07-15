import { supabase } from "@/utils/supabase";
import type { NextApiRequest, NextApiResponse } from "next";
import Stripe from "stripe";

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

  const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
    apiVersion: "2022-11-15",
  });

  const body = req.body;

  const consumer = await stripe.customers.create({
    name: body.record.id,
  });

  const subscription = await stripe.subscriptions.create({
    customer: consumer.id,
    items: [
      { price: "price_1NTKPTBcUfXYxWWVOfMFn9DA" },
      { price: "price_1NTKOIBcUfXYxWWVJnXsjccc" },
      { price: "price_1NTKNHBcUfXYxWWVVmx8QMSI" },
      { price: "price_1NSdc4BcUfXYxWWVmuu2ODKM" },
      { price: "price_1NSdayBcUfXYxWWVGEjTuBEF" },
    ],
  });

  const workspace = await supabase
    .from("workspaces")
    .update({ consumer_id: consumer.id, subscription_id: subscription.id })
    .eq("id", body.record.id)
    .select();

  res.status(200).json({ workspace });
}
