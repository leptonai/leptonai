import { cors } from "@/utils/cors";
import { stripeClient } from "@/utils/stripe/stripe-client";
import { getWorkspaceById } from "@/utils/workspace";
import {
  NextApiWithSupabaseHandler,
  serverClientWithAuthorized,
} from "@/utils/supabase";

// Get the stripe portal URL for a workspace
const handler: NextApiWithSupabaseHandler = async (req, res, supabase) => {
  try {
    const workspaceId = req.body.workspace_id;
    const workspace = await getWorkspaceById(workspaceId, supabase);
    if (!workspace) {
      return res.status(401).send("You are not authorized to call this API");
    } else {
      const consumerId = workspace.consumer_id;
      if (!consumerId) {
        return res.status(412).send("Workspace has no consumer_id");
      }
      const session = await stripeClient.billingPortal.sessions.create({
        customer: consumerId,
        return_url: `https://dashboard.lepton.ai/workspace/${workspaceId}/settings/billing`,
      });
      res.status(200).json({ url: session.url });
    }
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.status(500).send(`Error: ${errorMessage}`);
  }
};

export default cors(serverClientWithAuthorized(handler));
