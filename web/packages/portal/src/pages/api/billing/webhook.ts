import { stripeClient } from "@/utils/stripe/stripe-client";
import { updateCustomerAmountGTE } from "@/utils/stripe/update-subscription";
import { supabaseAdminClient } from "@/utils/supabase";
import { buffer } from "micro";
import type { NextApiHandler } from "next";
import Stripe from "stripe";
import { updateWorkspaceByConsumerId } from "@/utils/workspace";
import { withLogging } from "@/utils/logging";

export const config = { api: { bodyParser: false } };

/**
 * @openapi
 * /api/billing/webhook:
 *   post:
 *     operationId: billingWebhook
 *     summary: Stripe webhook
 *     description: |
 *       This endpoint is used by Stripe to send events to the server.
 *
 *       Events handled:
 *         - `customer.subscription.updated`
 *           * Update workspace status based on subscription status
 *         - `customer.subscription.created`
 *           * Update workspace status based on subscription status
 *         - `payment_method.attached`
 *           * Update workspace payment_method_attached
 *         - `payment_method.detached`
 *           * Update workspace payment_method_attached
 *     tags: [Billing]
 *     parameters:
 *       - in: header
 *         name: stripe-signature
 *         description: The signature of the event
 *         required: true
 *         schema:
 *           type: string
 *     responses:
 *       200:
 *         description: Success
 *         schema:
 *           - type: string
 *
 */
const handler: NextApiHandler<Stripe.Event | string> = async (req, res) => {
  const sig = req.headers["stripe-signature"]!;
  let event;

  const reqBuffer = await buffer(req);

  try {
    event = stripeClient.webhooks.constructEvent(
      reqBuffer,
      sig,
      process.env.STRIPE_SIGNING_SECRET!
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
          const uncollectableInvoices = await stripeClient.invoices.list({
            subscription: subscription.id,
            status: "uncollectible",
            limit: 1,
          });

          const openInvoices = await stripeClient.invoices.list({
            subscription: subscription.id,
            status: "open",
            limit: 1,
          });

          const hasUnpaidInvoice =
            uncollectableInvoices.data.length > 0 ||
            openInvoices.data.length > 0;

          const status: Stripe.Subscription.Status = hasUnpaidInvoice
            ? "past_due"
            : "active";

          if (status === "past_due") {
            // TODO: mothership terminate workspace if active
          }
          if (status === "active") {
            // TODO: mothership resume workspace if terminate
          }
          await supabaseAdminClient
            .from("workspaces")
            .update({ status })
            .eq("id", subscription.metadata.workspace_id);
          res
            .status(200)
            .send(
              `Update workspace ${subscription.metadata.workspace_id} to ${status}`
            );
          return;
        } else {
          res
            .status(500)
            .send(`No workspace id found for subscription ${subscription.id}`);
          return;
        }
      case "payment_method.attached":
        const paymentMethodAttached = event.data.object as Stripe.PaymentMethod;
        const { error: updateError } = await updateWorkspaceByConsumerId(
          paymentMethodAttached.customer as string,
          { payment_method_attached: true },
          supabaseAdminClient
        );

        if (updateError) {
          res.statusMessage = updateError.message;
          res.status(500).send(`Error: ${updateError.message}`);
          return;
        }

        const incrementIds = await updateCustomerAmountGTE(
          paymentMethodAttached.customer as string,
          5000
        );
        res
          .status(200)
          .send(`Update subscriptions ${incrementIds.join(",")} to gte 5000`);
        return;
      case "payment_method.detached":
        const paymentMethodDetached = event.data.object as Stripe.PaymentMethod;
        const paymentMethods = await stripeClient.paymentMethods
          .list({
            customer: paymentMethodDetached.customer as string,
          })
          .autoPagingToArray({ limit: 1 });

        if (paymentMethods.length === 0) {
          const { error: updateError } = await updateWorkspaceByConsumerId(
            paymentMethodDetached.customer as string,
            { payment_method_attached: false },
            supabaseAdminClient
          );

          if (updateError) {
            res.statusMessage = updateError.message;
            res.status(500).send(`Error: ${updateError.message}`);
            return;
          }

          const decrementIds = await updateCustomerAmountGTE(
            paymentMethodDetached.customer as string,
            50
          );
          res
            .status(200)
            .send(`Update subscriptions ${decrementIds.join(",")} to gte 50`);
        } else {
          res.status(200).json(event);
          return;
        }
        return;
      default:
        res.status(200).json(event);
        return;
    }
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.statusMessage = errorMessage;
    res.status(500).send(`Error: ${errorMessage}`);
    return;
  }
};

export default withLogging(handler);
