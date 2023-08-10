import { cors } from "@/utils/cors";
import { stripeClient } from "@/utils/stripe/stripe-client";
import { getWorkspaceById } from "@/utils/workspace";
import {
  NextApiWithSupabaseHandler,
  serverClientWithAuthorized,
} from "@/utils/supabase";
import { withLogging } from "@/utils/logging";

// Get the invoice data for a workspace
const handler: NextApiWithSupabaseHandler = async (req, res, supabase) => {
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
