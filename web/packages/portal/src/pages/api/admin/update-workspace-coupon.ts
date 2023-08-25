import { getAvailableCoupons } from "@/utils/stripe/available-coupons";
import { getStripeClient } from "@/utils/stripe/stripe-client";
import { supabaseAdminClient } from "@/utils/supabase";
import {
  getWorkspaceById,
  updateWorkspaceByConsumerId,
} from "@/utils/workspace";
import type { NextApiRequest, NextApiResponse } from "next";
import { withLogging } from "@/utils/logging";

// Update consumer coupon
async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (
    req.method !== "POST" ||
    req.query.LEPTON_API_SECRET !== process.env.LEPTON_API_SECRET
  ) {
    return res.status(401).send("You are not authorized to call this API");
  }

  try {
    const workspaceId = req.body.workspace_id;
    const coupon = req.body.coupon;
    const workspace = await getWorkspaceById(workspaceId, supabaseAdminClient);
    if (!workspace) {
      res.status(412).send("No workspace found");
    } else {
      const stripeClient = getStripeClient(workspace.chargeable);
      const couponId = getAvailableCoupons(coupon, workspace.chargeable);
      const consumerId = workspace.consumer_id!;
      if (coupon === "0") {
        await stripeClient.customers.deleteDiscount(consumerId);
        const { error: updateError } = await updateWorkspaceByConsumerId(
          consumerId,
          { coupon_id: null },
          supabaseAdminClient
        );
        if (updateError) {
          res.statusMessage = updateError.message;
          res.status(500).send(`Error: ${updateError.message}`);
          return;
        }
        res.status(200).send(`Delete coupon for ${consumerId}`);
      } else {
        if (couponId && consumerId) {
          await stripeClient.customers.update(consumerId, {
            coupon: couponId,
          });
          const { error: updateError } = await updateWorkspaceByConsumerId(
            consumerId,
            { coupon_id: couponId },
            supabaseAdminClient
          );
          if (updateError) {
            res.statusMessage = updateError.message;
            res.status(500).send(`Error: ${updateError.message}`);
            return;
          }
          res.status(200).send(`Coupon ${coupon} applied to ${consumerId}`);
        } else {
          res.status(412).send("No coupon or consumer found");
        }
      }
    }
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.statusMessage = errorMessage;
    res.status(500).send(`Error: ${errorMessage}`);
  }
}

export default withLogging(handler);
