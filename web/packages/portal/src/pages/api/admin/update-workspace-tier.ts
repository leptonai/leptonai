import { updateSubscriptionItems } from "@/utils/stripe/update-subscription";
import { supabaseAdminClient } from "@/utils/supabase";
import { getWorkspaceById } from "@/utils/workspace";
import type { NextApiRequest, NextApiResponse } from "next";
import { withLogging } from "@/utils/logging";

// Update workspace tier
async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (
    req.method !== "POST" ||
    req.query.LEPTON_API_SECRET !== process.env.LEPTON_API_SECRET
  ) {
    return res.status(401).send("You are not authorized to call this API");
  }

  try {
    const workspaceId = req.body.workspace_id;
    const tier = req.body.tier;
    const workspace = await getWorkspaceById(workspaceId, supabaseAdminClient);
    if (tier !== "Standard" && tier !== "Basic" && tier !== "Enterprise") {
      res.status(412).send('tier must be "Basic" | "Standard" | "Enterprise"');
    }
    if (!workspace || !workspace.subscription_id) {
      res.status(412).send("No workspace or subscription found");
    } else {
      await updateSubscriptionItems(
        workspace.subscription_id,
        workspace.chargeable,
        tier
      );
      await supabaseAdminClient
        .from("workspaces")
        .update({ tier })
        .eq("id", workspaceId);

      res
        .status(200)
        .send(`update workspace tier to ${tier} for ${workspaceId}`);
    }
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.statusMessage = errorMessage;
    res.status(500).send(`Error: ${errorMessage}`);
  }
}

export default withLogging(handler);
