import { stripeClient } from "@/utils/stripe";
import { supabase } from "@/utils/supabase";
import { buffer } from "micro";
import type { NextApiRequest, NextApiResponse } from "next";
import Stripe from "stripe";
export const config = { api: { bodyParser: false } };

async function updateSubscriptions(consumerId: string, amountGTE: number) {
  const { data: subscriptions } = await stripeClient.subscriptions.search({
    query: `status:'active' AND metadata['consumer_id']:'${consumerId}'`,
  });
  await Promise.all(
    subscriptions.map(async ({ id }) => {
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
      case "customer.subscription.updated":
        const customerSubscriptionUpdated = event.data
          .object as Stripe.Subscription;
        if (
          customerSubscriptionUpdated.metadata &&
          customerSubscriptionUpdated.metadata.workspace_id
        ) {
          if (customerSubscriptionUpdated.status === "past_due") {
            // TODO: mothership terminate workspace if active
          }
          if (customerSubscriptionUpdated.status === "active") {
            // TODO: mothership resume workspace if terminate
          }
          await supabase
            .from("workspaces")
            .update({ status: customerSubscriptionUpdated.status })
            .eq("id", customerSubscriptionUpdated.metadata.workspace_id);
          res
            .status(200)
            .send(
              `Update workspace ${customerSubscriptionUpdated.metadata.workspace_id} to ${customerSubscriptionUpdated.status}`,
            );
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
