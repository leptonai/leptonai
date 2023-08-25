import { getStripeClient } from "@/utils/stripe/stripe-client";
import { retrieveSubscriptionItem } from "@/utils/stripe/retrieve-subscription-item";
import { supabaseAdminClient } from "@/utils/supabase";
import { withLogging } from "@/utils/logging";
import { getWorkspaceById } from "@/utils/workspace";
import type Stripe from "stripe";
import { NextApiHandler } from "next";

/**
 * @openapi
 * definitions:
 *   UsageRecord:
 *     type: object
 *     description: A [usage record](https://stripe.com/docs/api/usage_records/object)
 */
type UsageRecord = Stripe.UsageRecord;

/**
 * @openapi
 * definitions:
 *   ReportComputeUsageRecord:
 *       type: object
 *       required: [id, workspace_id, shape, usage, end_time]
 *       properties:
 *         id:
 *           type: string
 *         workspace_id:
 *           type: string
 *           description: The workspace ID
 *         shape:
 *           type: string
 *           description: The shape of the compute instance
 *         usage:
 *           type: number
 *           description: The usage quantity for the specified date
 *           format: float
 *           minimum: 0
 *         end_time:
 *           type: string
 *           description: The timestamp when this usage occurred
 *           format: date-time
 *   ReportComputeUsageBody:
 *     type: object
 *     required: [record]
 *     properties:
 *       record:
 *         description: The usage report record
 *         $ref: '#/definitions/ReportComputeUsageRecord'
 */
interface ReportComputeUsageBody {
  record: {
    id: string;
    workspace_id: string;
    shape: string;
    usage: number;
    end_time: string;
  };
}

/**
 * @openapi
 * /api/billing/report-compute:
 *   post:
 *     operationId: reportComputeUsage
 *     summary: Report compute usage to stripe
 *     tags: [Billing]
 *     security:
 *       - serverAuth: [admin]
 *     parameters:
 *       - in: body
 *         name: body
 *         description: Usage record
 *         required: true
 *         schema:
 *           $ref: '#/definitions/ReportComputeUsageBody'
 *     responses:
 *       200:
 *         description: The usage record
 *         schema:
 *           $ref: '#/definitions/UsageRecord'
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
const handler: NextApiHandler<UsageRecord | string> = async (req, res) => {
  console.log("report-compute", JSON.stringify(req.body));
  if (
    req.method !== "POST" ||
    req.query.LEPTON_API_SECRET !== process.env.LEPTON_API_SECRET
  ) {
    return res.status(401).send("You are not authorized to call this API");
  }

  try {
    const body: ReportComputeUsageBody = req.body;
    const id = body.record.id;
    const workspaceId = body.record.workspace_id;
    const shape = body.record.shape;
    const usage = body.record.usage;
    const timestamp = Math.round(
      new Date(body.record.end_time).getTime() / 1000
    );

    const workspace = await getWorkspaceById(workspaceId, supabaseAdminClient);

    if (!workspace) {
      return res.status(412).send("No workspace found");
    }

    const subscriptionItem = await retrieveSubscriptionItem(
      shape,
      workspace.chargeable,
      workspace.subscription_id
    );

    if (!subscriptionItem) {
      return res.status(412).send("No subscription shape matched");
    }

    const stripeClient = getStripeClient(workspace.chargeable);

    const usageRecord = await stripeClient.subscriptionItems.createUsageRecord(
      subscriptionItem.id,
      { quantity: usage, timestamp },
      {
        idempotencyKey: id,
      }
    );

    await supabaseAdminClient
      .from("compute_hourly")
      .update({ stripe_usage_record_id: usageRecord.id })
      .eq("id", id);

    res.status(200).json(usageRecord);
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.statusMessage = errorMessage;
    res.status(500).send(`Error: ${errorMessage}`);
  }
};

export default withLogging(handler);
