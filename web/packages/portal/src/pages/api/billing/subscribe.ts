import { AvailableCoupons } from "@/utils/stripe/available-coupons";
import { AvailableProducts } from "@/utils/stripe/available-products";
import { stripeClient } from "@/utils/stripe/stripe-client";
import { supabaseAdminClient } from "@/utils/supabase";
import type { NextApiHandler } from "next";
import { withLogging } from "@/utils/logging";

/**
 * @openapi
 * definitions:
 *   SubscribeRecord:
 *     type: object
 *     required: [id]
 *     properties:
 *       id:
 *         type: string
 *         description: The workspace ID
 *   SubscribeBody:
 *     type: object
 *     required: [record]
 *     properties:
 *       record:
 *         description: The subscription record
 *         $ref: '#/definitions/SubscribeRecord'
 */
interface SubscribeBody {
  record: {
    id: string;
  };
}

/**
 * @openapi
 * definitions:
 *   SubscribeResponse:
 *     type: object
 *     required: [consumer_id, subscription_id]
 *     properties:
 *       consumer_id:
 *         type: string
 *         description: The Stripe customer ID
 *       subscription_id:
 *         type: string
 *         description: The Stripe subscription ID
 */
interface SubscribeResponse {
  consumer_id: string;
  subscription_id: string;
}

/**
 * @openapi
 * /api/billing/subscribe:
 *   post:
 *     operationId: planSubscribe
 *     summary: Subscribe a workspace to a plan
 *     tags: [Billing]
 *     security:
 *       - serverAuth: [admin]
 *     parameters:
 *       - in: body
 *         name: body
 *         description: Subscription record
 *         required: true
 *         schema:
 *           $ref: '#/definitions/SubscribeBody'
 *     responses:
 *       200:
 *         description: The subscription record
 *         schema:
 *           $ref: '#/definitions/SubscribeResponse'
 *       401:
 *         description: Unauthorized
 *         schema:
 *           type: string
 *       500:
 *         description: Internal server error
 *         schema:
 *           type: string
 */
const handler: NextApiHandler<SubscribeResponse | string> = async (
  req,
  res
) => {
  if (
    req.method !== "POST" ||
    req.query.LEPTON_API_SECRET !== process.env.LEPTON_API_SECRET
  ) {
    return res.status(401).send("You are not authorized to call this API");
  }

  try {
    const body: SubscribeBody = req.body;
    const workspace_id = body.record.id;

    const coupon = AvailableCoupons["10"];

    const consumer = await stripeClient.customers.create({
      metadata: {
        workspace_id,
      },
      coupon,
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
    });

    const updated = {
      consumer_id: consumer.id,
      subscription_id: subscription.id,
    };

    await supabaseAdminClient
      .from("workspaces")
      .update({
        consumer_id: consumer.id,
        subscription_id: subscription.id,
        coupon_id: coupon,
      })
      .eq("id", workspace_id);

    res.status(200).json(updated);
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.statusMessage = errorMessage;
    res.status(500).send(`Error: ${errorMessage}`);
  }
};

export default withLogging(handler);
