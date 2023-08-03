import { AvailableCoupons } from "@/utils/stripe/available-coupons";
import { stripeClient } from "@/utils/stripe/stripe-client";
import type { NextApiRequest, NextApiResponse } from "next";

// Update subscription coupon
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
    const subscriptionId = req.body.subscription_id;
    const coupon = req.body.coupon;
    const couponId = AvailableCoupons[coupon];

    if (coupon && couponId && subscriptionId) {
      await stripeClient.subscriptions.update(subscriptionId, {
        coupon: couponId,
      });
      res.status(200).send(`Coupon ${coupon} applied to ${subscriptionId}`);
    } else {
      res.status(412).send("No coupon or subscription found");
    }
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.status(500).send(`Error: ${errorMessage}`);
  }
}
