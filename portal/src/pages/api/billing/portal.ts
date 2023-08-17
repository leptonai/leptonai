import { cors } from "@/utils/cors";
import { stripeClient } from "@/utils/stripe/stripe-client";
import { getWorkspaceById } from "@/utils/workspace";
import {
  NextApiWithSupabaseHandler,
  serverClientWithAuthorized,
} from "@/utils/supabase";
import { withLogging } from "@/utils/logging";

// Get the stripe portal URL for a workspace
/**
 * @openapi
 * /api/billing/portal:
 *   post:
 *     operationId: getBillingPortal
 *     summary: Get billing portal URL
 *     tags: [Billing]
 *     security:
 *       - cookieAuth: [user]
 *     parameters:
 *       - in: body
 *         name: body
 *         description: Workspace ID
 *         required: true
 *         schema:
 *           type: object
 *           required: [workspace_id]
 *           properties:
 *             workspace_id:
 *               type: string
 *     responses:
 *       200:
 *         description: Billing portal URL
 *         schema:
 *           type: object
 *           required: [url]
 *           properties:
 *             url:
 *               type: string
 *               format: url
 *               description: Billing portal URL
 *       401:
 *         description: Unauthorized
 *         schema:
 *           type: string
 *       412:
 *         description: Precondition failed
 *         schema:
 *           type: string
 *       500:
 *         description: Internal server error
 *         schema:
 *           type: string
 */
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
    res.statusMessage = errorMessage;
    res.status(500).send(`Error: ${errorMessage}`);
  }
};

export default withLogging(cors(serverClientWithAuthorized(handler)));
