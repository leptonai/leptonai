import { cors } from "@/utils/cors";
import { stripeClient } from "@/utils/stripe/stripe-client";
import { getWorkspaceById } from "@/utils/workspace";
import { NextApiRequest, NextApiResponse } from "next";

// Get the invoice data for a workspace
async function handler(req: NextApiRequest, res: NextApiResponse) {
  try {
    const workspaceId = req.body.workspace_id;
    const workspace = await getWorkspaceById(workspaceId, req.cookies);
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
      const {
        data: [draft],
      } = await stripeClient.invoices.list({
        subscription,
        status: "draft",
      });
      const upcoming = await stripeClient.invoices.retrieveUpcoming({
        subscription,
      });
      const { data: products } = await stripeClient.products.list({
        active: true,
        expand: ["data.default_price.tiers"],
      });
      res.status(200).json({
        open,
        upcoming: draft || upcoming,
        products,
      });
    }
  } catch (err) {
    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    res.status(500).send(`Error: ${errorMessage}`);
  }
}

export default cors(handler);
