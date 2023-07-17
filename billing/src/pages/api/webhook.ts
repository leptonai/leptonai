import { stripeClient } from "@/utils/stripe";
import { supabase } from "@/utils/supabase";
import { buffer } from "micro";
import type { NextApiRequest, NextApiResponse } from "next";
import Stripe from "stripe";
export const config = { api: { bodyParser: false } };

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  const sig = req.headers["stripe-signature"]!;
  let event;

  const reqBuffer = await buffer(req);

  try {
    event = stripeClient.webhooks.constructEvent(
      reqBuffer,
      sig,
      process.env.STRIPE_ENDPOINT_SECRET!,
    );
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : "Unknown error";
    if (err! instanceof Error) console.log(err);
    console.log(`❌ Error: ${errorMessage}`);
    res.status(400).send(`Error: ${errorMessage}`);
    return;
  }

  switch (event.type) {
    case "customer.subscription.updated":
      const subscription = event.data.object as Stripe.Subscription;
      if (subscription.metadata && subscription.metadata.workspace_id) {
        try {
          if (subscription.status === "past_due") {
            // TODO: mothership terminate workspace if active
          }
          if (subscription.status === "active") {
            // TODO: mothership resume workspace if terminate
          }
          await supabase
            .from("workspaces")
            .update({ status: subscription.status })
            .eq("id", subscription.metadata.workspace_id);
          console.log(
            `Update workspace ${subscription.metadata.workspace_id} to ${subscription.status}`,
          );
          res.status(200).json(subscription);
        } catch (err) {
          const errorMessage =
            err instanceof Error ? err.message : "Internal server error";
          res.status(500).send(`Error: ${errorMessage}`);
        }
      }
      break;
    // TODO: set billing_thresholds to minimal when payment deleted, and resume when paid
    default:
      res.status(200).json(event);
  }
}
