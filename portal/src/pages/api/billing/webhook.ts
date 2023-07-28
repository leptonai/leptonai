import { stripeClient } from "@/utils/stripe";
import { supabaseAdminClient } from "@/utils/supabase";
import { buffer } from "micro";
import type { NextApiRequest, NextApiResponse } from "next";
import Stripe from "stripe";
export const config = { api: { bodyParser: false } };

async function updateSubscriptions(customer: string, amountGTE: number) {
  const { data: subscriptions } = await stripeClient.subscriptions.list({
    customer,
  });
  await Promise.all(
    subscriptions
      .filter(({ status }) => status === "active")
      .map(async ({ id }) => {
        await stripeClient.subscriptions.update(id, {
          billing_thresholds: {
            amount_gte: amountGTE,
            reset_billing_cycle_anchor: false,
          },
        });
      }),
  );
  return subscriptions.map(({ id }) => id);
}

// Update workspace status based on subscription status
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
      process.env.STRIPE_SIGNING_SECRET!,
    );
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : "Unknown error";
    if (err! instanceof Error) console.log(err);
    res.status(400).send(`Error: ${errorMessage}`);
    return;
  }
  try {
    switch (event.type) {
      case "customer.subscription.created":
      case "customer.subscription.updated":
        const subscription = event.data.object as Stripe.Subscription;
        if (subscription.metadata.workspace_id) {
          if (subscription.status === "past_due") {
            // TODO: mothership terminate workspace if active
          }
          if (subscription.status === "active") {
            // TODO: mothership resume workspace if terminate
          }
          await supabaseAdminClient
            .from("workspaces")
            .update({ status: subscription.status })
            .eq("id", subscription.metadata.workspace_id);
          res
            .status(200)
            .send(
              `Update workspace ${subscription.metadata.workspace_id} to ${subscription.status}`,
            );
        } else {
          res
            .status(500)
            .send(`No workspace id found for subscription ${subscription.id}`);
        }
        break;
      case "payment_method.attached":
        const paymentMethodAttached = event.data.object as Stripe.PaymentMethod;
        const incrementIds = await updateSubscriptions(
          paymentMethodAttached.customer as string,
          5000,
        );
        res
          .status(200)
          .send(`Update subscriptions ${incrementIds.join(",")} to gte 5000`);
        break;
      case "payment_method.detached":
        const paymentMethodDetached = event.data.object as Stripe.PaymentMethod;
        const decrementIds = await updateSubscriptions(
          paymentMethodDetached.customer as string,
          50,
        );
        res
          .status(200)
          .send(`Update subscriptions ${decrementIds.join(",")} to gte 50`);
        break;
      default:
        res.status(200).json(event);
    }
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.status(500).send(`Error: ${errorMessage}`);
  }
}
