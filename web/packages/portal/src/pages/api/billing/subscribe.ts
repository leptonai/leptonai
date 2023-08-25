import { setupWorkspaceSubscription } from "@/utils/stripe/setup-workspace-subscription";
import { Database } from "@lepton/database";
import type { NextApiHandler } from "next";
import { withLogging } from "@/utils/logging";

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
 *           type: object
 *           description: workspace table schema
 *     responses:
 *       200:
 *         description: The subscription record
 *         schema:
 *           type: object
 *           description: workspace table schema
 *       401:
 *         description: Unauthorized
 *         schema:
 *           type: string
 *       500:
 *         description: Internal server error
 *         schema:
 *           type: string
 */
const handler: NextApiHandler<
  Database["public"]["Tables"]["workspaces"]["Update"] | string
> = async (req, res) => {
  if (
    req.method !== "POST" ||
    req.query.LEPTON_API_SECRET !== process.env.LEPTON_API_SECRET
  ) {
    return res.status(401).send("You are not authorized to call this API");
  }
  try {
    const workspace: Database["public"]["Tables"]["workspaces"]["Row"] =
      req.body.record;
    const workspaceId = workspace.id;
    const chargeable = workspace.chargeable;
    const updated = await setupWorkspaceSubscription(workspaceId, chargeable);
    res.status(200).json(updated);
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.statusMessage = errorMessage;
    res.status(500).send(`Error: ${errorMessage}`);
  }
};

export default withLogging(handler);
