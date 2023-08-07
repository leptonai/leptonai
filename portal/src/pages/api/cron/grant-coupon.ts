import { stripeClient } from "@/utils/stripe/stripe-client";
import { supabaseAdminClient } from "@/utils/supabase";
import { NextApiRequest, NextApiResponse } from "next";

const datesAreOnSameDay = (first: Date, second: Date) =>
  first.getFullYear() === second.getFullYear() &&
  first.getMonth() === second.getMonth() &&
  first.getDate() === second.getDate();

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  if (req.query.key !== "9dfb1916-374d-4d41-8887-b20422ffc89d") {
    res.status(401).end();
    return;
  }

  try {
    // 1. Select consumer_id, subscription_id and coupon_id where status equal active and coupon_id not null
    const { data: workspaces, error } = await supabaseAdminClient
      .from("workspaces")
      .select("id, consumer_id, subscription_id, coupon_id")
      .eq("status", "active")
      .not("coupon_id", "is", null)
      .not("consumer_id", "is", null)
      .not("subscription_id", "is", null);

    if (error) {
      return res.status(500).json({ error: error.message });
    }

    // 2. If the subscription.current_period_start equal now, then update the coupon to consumer_id
    const granted: { coupon_id: string; id: string }[] = [];
    const expired: { id: string }[] = [];
    if (workspaces && workspaces.length) {
      await Promise.all(
        workspaces.map((w) =>
          stripeClient.subscriptions.retrieve(w.subscription_id!).then((s) => {
            if (
              datesAreOnSameDay(
                new Date(s.current_period_start * 1000),
                new Date(),
              )
            ) {
              if (w.coupon_id) {
                granted.push({ id: w.id, coupon_id: w.coupon_id });
                return stripeClient.customers
                  .update(w.consumer_id!, {
                    coupon: w.coupon_id!,
                  })
                  .then(() => true);
              } else {
                expired.push({ id: w.id });
                return stripeClient.customers
                  .deleteDiscount(w.consumer_id!)
                  .then(() => true);
              }
            }
            return true;
          }),
        ),
      );
    }
    res.status(200).json({ granted, expired });
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.status(500).send(`Error: ${errorMessage}`);
  }
}
