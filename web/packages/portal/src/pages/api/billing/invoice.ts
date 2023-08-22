import { cors } from "@/utils/cors";
import { stripeClient } from "@/utils/stripe/stripe-client";
import { getWorkspaceById } from "@/utils/workspace";
import {
  NextApiWithSupabaseHandler,
  serverClientWithAuthorized,
} from "@/utils/supabase";
import { withLogging } from "@/utils/logging";
import type Stripe from "stripe";

/**
 * @openapi
 * definitions:
 *   Invoice:
 *     type: object
 *     required: [open, upcoming, list, products, current_period]
 *     properties:
 *       open:
 *         type: object
 *         description: Open [invoice](https://stripe.com/docs/api/invoices/object)
 *       upcoming:
 *         type: object
 *         description: Retrieve an [upcoming](https://stripe.com/docs/api/invoices/upcoming) invoice
 *       list:
 *         type: array
 *         description: |
 *           [Invoices](https://stripe.com/docs/api/invoices/list) for the
 *           subscription specified by `subscription_id` in the workspace record
 *         items:
 *           type: object
 *           description: |
 *             [Invoice](https://stripe.com/docs/api/invoices/object)
 *       products:
 *         type: array
 *         description: |
 *           All active [products](https://stripe.com/docs/api/products/list)
 *           with their default prices and tiers
 *         items:
 *           type: object
 *           description: |
 *             [Product](https://stripe.com/docs/api/products/object) with
 *             default price and tiers
 *       coupon:
 *         type: object
 *         description: |
 *           [Coupon](https://stripe.com/docs/api/coupons/object) applied to the
 *           workspace
 *         nullable: true
 *       current_period:
 *         type: object
 *         description: Current period start and end dates
 *         properties:
 *           start:
 *             type: integer
 *             description: Current period start date in milliseconds
 *           end:
 *             type: integer
 *             description: Current period end date in milliseconds
 */
interface Invoice {
  open: Stripe.Invoice;
  upcoming: Stripe.UpcomingInvoice;
  list: Stripe.Invoice[];
  products: Stripe.Product[];
  coupon: Stripe.Coupon | null;
  current_period: {
    start: number;
    end: number;
  };
}

/**
 * @openapi
 * /api/billing/invoice:
 *   post:
 *     operationId: getInvoice
 *     summary: Get invoice data for a workspace
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
 *         description: Invoice data
 *         schema:
 *           $ref: '#/definitions/Invoice'
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
const handler: NextApiWithSupabaseHandler<Invoice | string> = async (
  req,
  res,
  supabase
) => {
  try {
    const workspaceId = req.body.workspace_id;
    const workspace = await getWorkspaceById(workspaceId, supabase);
    if (!workspace) {
      return res.status(401).send("You are not authorized to call this API");
    } else {
      const subscription = workspace.subscription_id;
      if (!subscription) {
        return res.status(412).send("Workspace has no subscription");
      }
      const {
        data: [open],
      } = await stripeClient.invoices.list({
        subscription,
        status: "open",
      });
      const coupon = workspace.coupon_id
        ? await stripeClient.coupons.retrieve(workspace.coupon_id)
        : null;
      const { data: invoiceList } = await stripeClient.invoices.list({
        subscription,
      });

      const { current_period_start, current_period_end } =
        await stripeClient.subscriptions.retrieve(subscription);

      const upcoming = await stripeClient.invoices.retrieveUpcoming({
        subscription,
      });
      const { data: products } = await stripeClient.products.list({
        active: true,
        expand: ["data.default_price.tiers"],
      });
      res.status(200).json({
        open,
        upcoming,
        list: invoiceList,
        products,
        coupon,
        current_period: {
          start: current_period_start * 1000,
          end: current_period_end * 1000,
        },
      });
    }
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.statusMessage = errorMessage;
    res.status(500).send(`Error: ${errorMessage}`);
  }
};

export default withLogging(cors(serverClientWithAuthorized(handler)));
