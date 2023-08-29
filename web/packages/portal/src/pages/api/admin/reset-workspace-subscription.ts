import { setupWorkspaceSubscription } from "@/utils/stripe/setup-workspace-subscription";
import { getStripeClient } from "@/utils/stripe/stripe-client";
import { supabaseAdminClient } from "@/utils/supabase";
import { getWorkspaceById } from "@/utils/workspace";
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
    const chargeable = req.body.chargeable;
    const workspace = await getWorkspaceById(workspaceId, supabaseAdminClient);
    if (!workspace) {
      res.status(412).send("No workspace found");
    } else {
      const previousStripeClient = getStripeClient(workspace.chargeable);
      if (workspace.subscription_id) {
        try {
          await previousStripeClient.subscriptions.del(
            workspace.subscription_id
          );
        } catch (e) {
          console.warn(e);
        }
      }
      if (workspace.consumer_id) {
        try {
          await previousStripeClient.customers.deleteDiscount(
            workspace.consumer_id
          );
        } catch (e) {
          console.warn(e);
        }
        try {
          await previousStripeClient.customers.del(workspace.consumer_id);
        } catch (e) {
          console.warn(e);
        }
      }
      const updated = await setupWorkspaceSubscription(
        workspaceId,
        chargeable,
        workspace.tier
      );
      res.status(200).json(updated);
    }
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.statusMessage = errorMessage;
    res.status(500).send(`Error: ${errorMessage}`);
  }
}

export default withLogging(handler);
